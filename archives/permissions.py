"""Politique RBAC MVP centralisée des archives.

La matrice est volontairement provisoire jusqu’à validation par C-Tech. Elle ne
introduit aucune ACL de service ou attribution nominative.
"""

from django.db.models import QuerySet

from accounts.models import Role

from .models import Archive, ConfidentialityLevel


ADMIN_VISIBLE_LEVELS = frozenset(ConfidentialityLevel.values)
AGENT_VISIBLE_LEVELS = frozenset(
    {ConfidentialityLevel.PUBLIC, ConfidentialityLevel.INTERNAL}
)
CONSULTANT_VISIBLE_LEVELS = frozenset({ConfidentialityLevel.PUBLIC})


def visible_confidentiality_levels_for(user) -> frozenset[str]:
    """Retourne les niveaux d’archives visibles, deny-by-default sinon."""
    if not getattr(user, "is_authenticated", False):
        return frozenset()
    if user.is_superuser:
        return ADMIN_VISIBLE_LEVELS
    if user.role == Role.ADMINISTRATEUR:
        return ADMIN_VISIBLE_LEVELS
    if user.role == Role.AGENT_ARCHIVES:
        return AGENT_VISIBLE_LEVELS
    if user.role == Role.CONSULTANT:
        return CONSULTANT_VISIBLE_LEVELS
    return frozenset()


def has_archive_access(user) -> bool:
    """Indique si le compte possède un rôle métier reconnu ou est superuser."""
    return bool(visible_confidentiality_levels_for(user))


def visible_archives_for(user, queryset: QuerySet | None = None) -> QuerySet:
    """Filtre le QuerySet de base avant toute liste, recherche ou pagination."""
    queryset = queryset if queryset is not None else Archive.objects.all()
    levels = visible_confidentiality_levels_for(user)
    if not levels:
        return queryset.none()
    return queryset.filter(confidentiality_level__in=levels)


def can_view_archive(user, archive: Archive) -> bool:
    """Vérifie l’accès objet, en cohérence avec le filtrage de QuerySet."""
    return archive.confidentiality_level in visible_confidentiality_levels_for(user)


def can_create_archive(user) -> bool:
    """Autorise la création aux administrateurs métier, agents et superusers."""
    if not getattr(user, "is_authenticated", False):
        return False
    return user.is_superuser or user.role in {
        Role.ADMINISTRATEUR,
        Role.AGENT_ARCHIVES,
    }


def can_assign_confidentiality(user, confidentiality_level: str) -> bool:
    """Empêche une création ou une modification vers un niveau non autorisé."""
    if not can_create_archive(user):
        return False
    return confidentiality_level in visible_confidentiality_levels_for(user)


def can_update_archive(user, archive: Archive) -> bool:
    """Autorise la modification seulement si l’utilisateur voit l’archive."""
    return can_create_archive(user) and can_view_archive(user, archive)


def can_download_archive(user, archive: Archive) -> bool:
    """Le téléchargement suit strictement la même visibilité que le détail."""
    return can_view_archive(user, archive)
