"""Vues liées à l’authentification, au profil privé et à la feuille de route."""

from __future__ import annotations

import logging
from hashlib import sha256

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods, require_POST

from archives.permissions import visible_archives_for
from audit.models import AuditAction
from audit.services import get_client_ip, record_audit_event

from .forms import EmailAuthenticationForm, ProfileAvatarForm, SignUpForm
from .models import FutureImprovementFeature, FutureImprovementVote
from .security_views import start_pending_login
from .throttling import (
    format_wait,
    login_lockout_remaining,
    normalize_identifier,
    register_login_failure,
    register_signup,
    reset_login_failures,
    signup_allowed,
)


security_logger = logging.getLogger("ctech.security")


FUTURE_IMPROVEMENTS = (
    {
        "feature": FutureImprovementFeature.SEARCH_OCR,
        "description": "Indexation du contenu numérisé et filtres avancés pour retrouver plus vite un document.",
        "status": "Disponible",
        "icon": "search",
        "delivered": "Recherche plein texte dans les PDF, DOCX, XLSX et TXT, insensible aux accents, avec extraits. L’OCR des images reste à venir.",
        "link": "archives:list",
    },
    {
        "feature": FutureImprovementFeature.SIGNATURE,
        "description": "Circuits de validation traçables pour formaliser les approbations documentaires.",
        "status": "Prévu",
        "icon": "signature",
    },
    {
        "feature": FutureImprovementFeature.RETENTION,
        "description": "Alertes sur les échéances d’archivage, de révision et de conservation des dossiers.",
        "status": "Disponible",
        "icon": "calendar",
        "delivered": "Dates de révision et de fin de conservation, filtre par échéance et alertes sur le tableau de bord.",
        "link": "home",
    },
    {
        "feature": FutureImprovementFeature.ANALYTICS,
        "description": "Tableaux de bord exportables pour suivre l’activité, les accès et le cycle de vie des archives.",
        "status": "Disponible",
        "icon": "chart",
        "delivered": "Rapport d’activité imprimable par période et export CSV des archives filtrées, dans le seul périmètre visible.",
        "link": "report",
    },
    {
        "feature": FutureImprovementFeature.SECURITY,
        "description": "Double authentification et revue périodique des droits pour protéger davantage les accès.",
        "status": "Disponible",
        "icon": "shield",
        "delivered": "Double authentification TOTP avec codes de secours, et revue des droits pour les administrateurs.",
        "link": "two_factor",
    },
    {
        "feature": FutureImprovementFeature.CONNECTORS,
        "description": "Intégrations contrôlées avec les outils internes de C-Tech et les espaces documentaires autorisés.",
        "status": "Vision",
        "icon": "plug",
    },
)


def _fingerprint(identifier: str) -> str:
    """Empreinte courte permettant de corréler les journaux sans e-mail en clair."""
    return sha256(identifier.encode()).hexdigest()[:12] if identifier else "-"


class ThrottledLoginView(auth_views.LoginView):
    """Connexion par e-mail verrouillée temporairement après des échecs répétés."""

    template_name = "registration/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        identifier = normalize_identifier(request.POST.get("username"))
        remaining = login_lockout_remaining(identifier)
        if remaining:
            # Le formulaire n’est pas validé : aucun mot de passe n’est testé
            # pendant le verrouillage, même correct.
            return self._render_locked(identifier, remaining)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        identifier = normalize_identifier(self.request.POST.get("username"))
        locked_for = register_login_failure(identifier)
        security_logger.warning(
            "Login failure account=%s ip=%s locked=%s",
            _fingerprint(identifier),
            get_client_ip(self.request) or "-",
            bool(locked_for),
        )
        if locked_for:
            return self._render_locked(identifier, locked_for)
        return super().form_invalid(form)

    def form_valid(self, form):
        reset_login_failures(normalize_identifier(form.cleaned_data.get("username")))
        user = form.get_user()
        if user.totp_enabled:
            # Mot de passe correct, mais la session n’est ouverte qu’après le second facteur.
            start_pending_login(self.request, user, self.get_success_url())
            return redirect("login_verify")
        return super().form_valid(form)

    def _render_locked(self, identifier, seconds):
        form = self.get_form_class()(request=self.request, initial={"username": identifier})
        context = self.get_context_data(
            form=form,
            lockout_message=(
                "Trop de tentatives de connexion pour ce compte. "
                f"Réessayez dans {format_wait(seconds)}."
            ),
        )
        return self.render_to_response(context, status=429)


@require_http_methods(["GET", "POST"])
def signup(request):
    """Inscrit un consultant sans possibilité d’auto-attribution de privilèges."""

    if request.user.is_authenticated:
        return redirect("home")

    client_key = get_client_ip(request) or "unknown"
    if request.method == "POST":
        if not signup_allowed(client_key):
            security_logger.warning("Signup throttled ip=%s", client_key)
            return render(
                request,
                "registration/signup.html",
                {
                    "form": SignUpForm(),
                    "throttle_message": (
                        "Trop d’inscriptions récentes depuis cette connexion. "
                        "Réessayez plus tard."
                    ),
                },
                status=429,
            )
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            register_signup(client_key)
            login(request, user, backend="accounts.backends.EmailBackend")
            messages.success(request, "Votre compte Consultant a été créé avec succès.")
            return redirect("home")
    else:
        form = SignUpForm()

    return render(request, "registration/signup.html", {"form": form})


class AuditedPasswordChangeView(auth_views.PasswordChangeView):
    """Changement de mot de passe en libre-service, tracé dans le journal d’audit."""

    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("profile")

    def form_valid(self, form):
        response = super().form_valid(form)
        record_audit_event(
            actor=self.request.user,
            action=AuditAction.PASSWORD_CHANGE,
            request=self.request,
            details={"source": "web"},
        )
        messages.success(self.request, "Votre mot de passe a été modifié.")
        return response


@login_required
def future_improvements(request):
    """Présente la feuille de route et les votes de l’utilisateur connecté."""

    vote_counts = {
        entry["feature"]: entry["total"]
        for entry in FutureImprovementVote.objects.values("feature").annotate(total=Count("id"))
    }
    voted_features = set(
        FutureImprovementVote.objects.filter(user=request.user).values_list("feature", flat=True)
    )
    leading_count = max(vote_counts.values(), default=0)
    improvements = [
        {
            **improvement,
            "title": FutureImprovementFeature(improvement["feature"]).label,
            "vote_count": vote_counts.get(improvement["feature"], 0),
            "has_voted": improvement["feature"] in voted_features,
            "is_leading": leading_count > 0
            and vote_counts.get(improvement["feature"], 0) == leading_count,
        }
        for improvement in FUTURE_IMPROVEMENTS
    ]
    return render(
        request,
        "accounts/future_improvements.html",
        {
            "improvements": improvements,
            "leading_count": leading_count,
            "total_votes": sum(vote_counts.values()),
            "my_vote_count": len(voted_features),
        },
    )


@login_required
@require_POST
def toggle_future_improvement_vote(request):
    """Ajoute ou retire le vote de l’utilisateur, sans exposer les données des votants."""

    feature = request.POST.get("feature", "")
    if feature not in FutureImprovementFeature.values:
        raise Http404("Amélioration introuvable.")

    vote, created = FutureImprovementVote.objects.get_or_create(
        user=request.user,
        feature=feature,
    )
    feature_label = FutureImprovementFeature(feature).label
    if created:
        messages.success(request, f"Votre vote pour « {feature_label} » a été enregistré.")
    else:
        vote.delete()
        messages.info(request, f"Votre vote pour « {feature_label} » a été retiré.")
    return redirect("future_improvements")


@login_required
def profile(request):
    """Permet à l’utilisateur connecté de gérer son unique avatar privé."""

    if request.method == "POST" and request.POST.get("action") == "remove-avatar":
        if request.user.has_profile_avatar:
            request.user.profile_avatar = None
            request.user.profile_avatar_content_type = ""
            request.user.save(
                update_fields=["profile_avatar", "profile_avatar_content_type"]
            )
            messages.info(request, "Votre photo de profil a été retirée.")
        return redirect("profile")

    if request.method == "POST":
        form = ProfileAvatarForm(request.POST, request.FILES)
        if form.is_valid():
            avatar = form.cleaned_data["avatar"]
            request.user.profile_avatar = avatar.read()
            request.user.profile_avatar_content_type = avatar.content_type
            request.user.save(
                update_fields=["profile_avatar", "profile_avatar_content_type"]
            )
            messages.success(request, "Votre photo de profil a été mise à jour.")
            return redirect("profile")
    else:
        form = ProfileAvatarForm()

    context = {
        "form": form,
        "uploaded_archive_count": visible_archives_for(request.user)
        .filter(uploaded_by=request.user)
        .count(),
        "vote_count": FutureImprovementVote.objects.filter(user=request.user).count(),
    }
    return render(request, "accounts/profile.html", context)


@login_required
def profile_avatar(request, user_id: int):
    """Diffuse l’avatar uniquement au propriétaire authentifié du profil."""

    if request.user.pk != user_id or not request.user.has_profile_avatar:
        raise Http404("Avatar introuvable.")

    response = HttpResponse(
        bytes(request.user.profile_avatar),
        content_type=request.user.profile_avatar_content_type,
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
