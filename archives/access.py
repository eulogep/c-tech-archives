"""Mixins d’intégration de la politique RBAC centralisée des archives."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .permissions import (
    can_create_archive,
    can_update_archive,
    has_archive_access,
    visible_archives_for,
)


class ArchiveAuthorizationMixin(LoginRequiredMixin):
    """Exige une identité puis un rôle métier reconnu, superuser excepté."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not has_archive_access(request.user):
            raise PermissionDenied("Ce compte ne possède aucun accès métier aux archives.")
        return super().dispatch(request, *args, **kwargs)


class ArchiveVisibleQuerysetMixin(ArchiveAuthorizationMixin):
    """Expose un helper unique pour les listes et les vues ciblant une archive."""

    def visible_archive_queryset(self, queryset):
        return visible_archives_for(self.request.user, queryset)


class ArchiveCreatePermissionMixin(ArchiveAuthorizationMixin):
    """Refuse la création aux rôles qui n’ont qu’un droit de consultation."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not can_create_archive(request.user):
            raise PermissionDenied("La création d’archives n’est pas autorisée.")
        return super().dispatch(request, *args, **kwargs)


class ArchiveUpdatePermissionMixin(ArchiveVisibleQuerysetMixin):
    """Réserve la modification aux archives visibles et modifiables."""

    def get_object(self, queryset=None):
        queryset = self.visible_archive_queryset(queryset or super().get_queryset())
        archive = super().get_object(queryset)
        if not can_update_archive(self.request.user, archive):
            raise PermissionDenied("La modification de cette archive n’est pas autorisée.")
        return archive
