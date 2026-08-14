"""Vue de synthèse authentifiée du domaine documentaire."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from archives.models import ArchiveStatus, Category, DocumentType, Service
from archives.permissions import visible_archives_for


@login_required
def home(request):
    """Affiche des indicateurs agrégés limités au périmètre visible du rôle.

    Le RBAC T-011 filtre déjà les archives avant tout compteur. Le dashboard
    ne retourne aucune métadonnée individuelle et n’infère aucun niveau masqué.
    """
    visible_archives = visible_archives_for(request.user)
    context = {
        "archive_count": visible_archives.count(),
        "active_archive_count": visible_archives.filter(
            status=ArchiveStatus.ACTIVE
        ).count(),
        "archived_archive_count": visible_archives.filter(
            status=ArchiveStatus.ARCHIVED
        ).count(),
        "active_service_count": Service.objects.filter(
            is_active=True, archives__in=visible_archives
        ).distinct().count(),
        "active_category_count": Category.objects.filter(
            is_active=True, archives__in=visible_archives
        ).distinct().count(),
        "active_document_type_count": DocumentType.objects.filter(
            is_active=True, archives__in=visible_archives
        ).distinct().count(),
    }
    return render(request, "dashboard/home.html", context)
