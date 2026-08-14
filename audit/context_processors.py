"""Contexte de présentation de la consultation d’audit."""

from accounts.models import Role


def audit_policy(request):
    """Expose le lien d’audit seulement aux profils qui peuvent le consulter."""
    user = request.user
    return {
        "audit_policy": {
            "can_view": bool(
                user.is_authenticated
                and (user.is_superuser or user.role == Role.ADMINISTRATEUR)
            )
        }
    }
