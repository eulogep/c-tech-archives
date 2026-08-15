"""Journalisation des événements d’authentification réels via les signaux Django."""

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .models import AuditAction
from .services import record_audit_event


@receiver(user_logged_in)
def record_successful_login(sender, request, user, **kwargs):
    """Crée un événement LOGIN après une authentification réussie uniquement."""
    record_audit_event(
        actor=user,
        action=AuditAction.LOGIN,
        request=request,
        details={"source": "web"},
    )


@receiver(user_logged_out)
def record_successful_logout(sender, request, user, **kwargs):
    """Crée un événement LOGOUT lorsqu’un utilisateur authentifié se déconnecte."""
    if user is None or not user.is_authenticated:
        return
    record_audit_event(
        actor=user,
        action=AuditAction.LOGOUT,
        request=request,
        details={"source": "web"},
    )
