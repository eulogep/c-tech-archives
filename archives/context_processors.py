"""Contexte de présentation dérivé de la politique RBAC des archives."""

from .permissions import can_create_archive, has_archive_access


def archive_policy(request):
    """Fournit des indicateurs d’interface ; les vues gardent le contrôle serveur."""
    user = request.user
    return {
        "archive_policy": {
            "can_access": has_archive_access(user),
            "can_create": can_create_archive(user),
            "can_update": can_create_archive(user),
        }
    }
