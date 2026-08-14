"""Vue de synthèse authentifiée du domaine documentaire."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from archives.models import Archive, ArchiveStatus, Category, DocumentType, Service


@login_required
def home(request):
    """Affiche les indicateurs agrégés du MVP, sans métadonnée individuelle.

    La visibilité détaillée des archives sera définie au ticket T-011. Avant
    cette politique, le dashboard ne doit retourner aucune archive individuelle.
    """
    context = {
        "archive_count": Archive.objects.count(),
        "active_archive_count": Archive.objects.filter(status=ArchiveStatus.ACTIVE).count(),
        "archived_archive_count": Archive.objects.filter(status=ArchiveStatus.ARCHIVED).count(),
        "active_service_count": Service.objects.filter(is_active=True).count(),
        "active_category_count": Category.objects.filter(is_active=True).count(),
        "active_document_type_count": DocumentType.objects.filter(is_active=True).count(),
    }
    return render(request, "dashboard/home.html", context)
