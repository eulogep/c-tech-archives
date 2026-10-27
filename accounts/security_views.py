"""Sécurité renforcée : double authentification TOTP et revue des droits.

Flux de connexion : le mot de passe est vérifié par ``ThrottledLoginView`` ;
si la double authentification est active, la session reçoit seulement une
connexion *en attente* (5 minutes) et l’utilisateur n’est connecté qu’après un
code TOTP valide ou un code de secours inutilisé.
"""

from __future__ import annotations

import time
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from audit.context_processors import audit_policy
from audit.models import AuditAction
from audit.services import record_audit_event

from . import totp
from .models import RecoveryCode, Role, User
from .throttling import format_wait, login_lockout_remaining, register_login_failure, reset_login_failures


PENDING_SESSION_KEY = "ctech_2fa_pending"
SETUP_SESSION_KEY = "ctech_2fa_setup_secret"
NEW_CODES_SESSION_KEY = "ctech_2fa_new_codes"
PENDING_LIFETIME_SECONDS = 5 * 60
STALE_ACCOUNT_DAYS = 90


def start_pending_login(request, user, redirect_to: str):
    """Mémorise une connexion en attente du second facteur."""
    request.session.cycle_key()
    request.session[PENDING_SESSION_KEY] = {
        "user_id": user.pk,
        "backend": getattr(user, "backend", settings.AUTHENTICATION_BACKENDS[0]),
        "next": redirect_to,
        "issued": time.time(),
    }


def _qr_data_uri(uri: str) -> str:
    import segno

    return segno.make(uri, error="m").svg_data_uri(scale=5, border=2, dark="#15151f", light="#ffffff")


def _issue_recovery_codes(user) -> list[str]:
    codes = totp.generate_recovery_codes()
    RecoveryCode.objects.filter(user=user).delete()
    RecoveryCode.objects.bulk_create(
        RecoveryCode(user=user, code_hash=totp.hash_recovery_code(code)) for code in codes
    )
    return codes


def _consume_recovery_code(user, code: str) -> bool:
    match = RecoveryCode.objects.filter(
        user=user, code_hash=totp.hash_recovery_code(code), used_at__isnull=True
    ).first()
    if match is None:
        return False
    match.used_at = timezone.now()
    match.save(update_fields=["used_at"])
    return True


def _verify_second_factor(user, code: str) -> str | None:
    """Retourne « totp », « recovery » ou None ; met à jour l’anti-rejeu."""
    counter = totp.verify(user.totp_secret, code, last_counter=user.totp_last_counter)
    if counter is not None:
        user.totp_last_counter = counter
        user.save(update_fields=["totp_last_counter"])
        return "totp"
    if len("".join(character for character in code if character.isalnum())) == 10 and _consume_recovery_code(user, code):
        return "recovery"
    return None


@require_http_methods(["GET", "POST"])
def login_verify(request):
    """Deuxième étape de connexion : code TOTP ou code de secours."""
    pending = request.session.get(PENDING_SESSION_KEY)
    if not pending or time.time() - pending.get("issued", 0) > PENDING_LIFETIME_SECONDS:
        request.session.pop(PENDING_SESSION_KEY, None)
        messages.warning(request, "La vérification a expiré : reconnectez-vous.")
        return redirect("login")
    user = User.objects.filter(pk=pending["user_id"], is_active=True, totp_enabled=True).first()
    if user is None:
        request.session.pop(PENDING_SESSION_KEY, None)
        return redirect("login")

    identifier = f"2fa:{user.pk}"
    context = {"error": ""}
    if request.method == "POST":
        remaining = login_lockout_remaining(identifier)
        if remaining:
            context["error"] = f"Trop de codes erronés. Réessayez dans {format_wait(remaining)}."
            return render(request, "registration/login_verify.html", context, status=429)
        method = _verify_second_factor(user, request.POST.get("code", ""))
        if method:
            request.session.pop(PENDING_SESSION_KEY, None)
            reset_login_failures(identifier)
            login(request, user, backend=pending["backend"])
            if method == "recovery":
                left = RecoveryCode.objects.filter(user=user, used_at__isnull=True).count()
                record_audit_event(
                    actor=user, action=AuditAction.RECOVERY_CODE_USED, request=request,
                    details={"source": "web"},
                )
                messages.warning(
                    request,
                    f"Code de secours utilisé : il vous en reste {left}. Pensez à en générer de nouveaux.",
                )
            target = pending.get("next") or settings.LOGIN_REDIRECT_URL
            if not url_has_allowed_host_and_scheme(
                target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                target = settings.LOGIN_REDIRECT_URL
            return redirect(target)
        locked_for = register_login_failure(identifier)
        record_audit_event(
            actor=user, action=AuditAction.TWO_FACTOR_FAILURE, request=request, details={"source": "web"}
        )
        context["error"] = (
            f"Trop de codes erronés. Réessayez dans {format_wait(locked_for)}."
            if locked_for
            else "Code invalide. Vérifiez l’heure de votre téléphone et réessayez."
        )
        return render(
            request, "registration/login_verify.html", context, status=429 if locked_for else 200
        )
    return render(request, "registration/login_verify.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def two_factor(request):
    """Activation, désactivation et codes de secours de la double authentification."""
    user = request.user
    action = request.POST.get("action") if request.method == "POST" else None

    if action == "enable" and not user.totp_enabled:
        secret = request.session.get(SETUP_SESSION_KEY, "")
        counter = totp.verify(secret, request.POST.get("code", ""))
        if counter is None:
            messages.error(request, "Code invalide : la double authentification n’est pas activée.")
            return redirect("two_factor")
        with transaction.atomic():
            user.totp_secret = secret
            user.totp_enabled = True
            user.totp_last_counter = counter
            user.save(update_fields=["totp_secret", "totp_enabled", "totp_last_counter"])
            request.session[NEW_CODES_SESSION_KEY] = _issue_recovery_codes(user)
            record_audit_event(
                actor=user, action=AuditAction.TWO_FACTOR_ENABLE, request=request, details={"source": "web"}
            )
        request.session.pop(SETUP_SESSION_KEY, None)
        messages.success(request, "Double authentification activée. Conservez vos codes de secours.")
        return redirect("two_factor")

    if action in {"disable", "regenerate"} and user.totp_enabled:
        if action == "disable" and not user.check_password(request.POST.get("password", "")):
            messages.error(request, "Mot de passe incorrect.")
            return redirect("two_factor")
        if not _verify_second_factor(user, request.POST.get("code", "")):
            messages.error(request, "Code invalide.")
            return redirect("two_factor")
        if action == "disable":
            with transaction.atomic():
                user.totp_secret = ""
                user.totp_enabled = False
                user.totp_last_counter = None
                user.save(update_fields=["totp_secret", "totp_enabled", "totp_last_counter"])
                RecoveryCode.objects.filter(user=user).delete()
                record_audit_event(
                    actor=user, action=AuditAction.TWO_FACTOR_DISABLE, request=request,
                    details={"source": "web"},
                )
            messages.info(request, "Double authentification désactivée.")
        else:
            request.session[NEW_CODES_SESSION_KEY] = _issue_recovery_codes(user)
            messages.success(request, "Nouveaux codes de secours générés ; les anciens sont révoqués.")
        return redirect("two_factor")

    context = {"new_codes": request.session.pop(NEW_CODES_SESSION_KEY, None)}
    if user.totp_enabled:
        context["codes_left"] = RecoveryCode.objects.filter(user=user, used_at__isnull=True).count()
    else:
        secret = request.session.get(SETUP_SESSION_KEY) or totp.generate_secret()
        request.session[SETUP_SESSION_KEY] = secret
        uri = totp.provisioning_uri(secret, user.email or user.username)
        context.update({"secret": totp.format_secret(secret), "qr": _qr_data_uri(uri)})
    return render(request, "accounts/two_factor.html", context)


@login_required
def access_review(request):
    """Revue périodique des droits : comptes, rôles, activité et second facteur."""
    if not audit_policy(request)["audit_policy"]["can_view"]:
        raise PermissionDenied("La revue des droits est réservée aux administrateurs.")
    stale_before = timezone.now() - timedelta(days=STALE_ACCOUNT_DAYS)
    users = User.objects.defer("profile_avatar").order_by("role", "email")
    role = request.GET.get("role", "")
    if role in Role.values:
        users = users.filter(role=role)
    focus = request.GET.get("focus", "")
    if focus == "no_2fa":
        users = users.filter(totp_enabled=False, is_active=True)
    elif focus == "stale":
        users = users.filter(is_active=True).filter(Q(last_login__lt=stale_before) | Q(last_login__isnull=True))
    elif focus == "privileged":
        users = users.filter(Q(role=Role.ADMINISTRATEUR) | Q(is_superuser=True) | Q(is_staff=True))

    active = User.objects.filter(is_active=True)
    summary = active.aggregate(
        total=Count("pk"),
        with_2fa=Count("pk", filter=Q(totp_enabled=True)),
        privileged=Count("pk", filter=Q(role=Role.ADMINISTRATEUR) | Q(is_superuser=True)),
        privileged_without_2fa=Count(
            "pk", filter=(Q(role=Role.ADMINISTRATEUR) | Q(is_superuser=True)) & Q(totp_enabled=False)
        ),
        stale=Count("pk", filter=Q(last_login__lt=stale_before) | Q(last_login__isnull=True)),
    )
    return render(
        request,
        "accounts/access_review.html",
        {
            "accounts": users,
            "summary": summary,
            "roles": Role.choices,
            "role_filter": role,
            "focus": focus,
            "stale_before": stale_before,
            "stale_days": STALE_ACCOUNT_DAYS,
        },
    )
