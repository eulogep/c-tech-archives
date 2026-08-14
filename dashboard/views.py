"""Vue de synthèse authentifiée du domaine documentaire."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from archives.models import Archive, ArchiveStatus, Category, DocumentType, Service


@login_required
def home(request):
    """Affiche les indicateurs MVP et les cinq dernières archives.

    Les compteurs sont volontairement simples et lisibles. Les relations des
    dernières archives sont préchargées afin de ne pas produire de requêtes N+1
    au rendu du template.
    """
    latest_archives = (
        Archive.objects.select_related("category", "document_type", "service", "uploaded_by")
        .order_by("-created_at")[:5]
    )
    context = {
        "archive_count": Archive.objects.count(),
        "active_archive_count": Archive.objects.filter(status=ArchiveStatus.ACTIVE).count(),
        "archived_archive_count": Archive.objects.filter(status=ArchiveStatus.ARCHIVED).count(),
        "active_service_count": Service.objects.filter(is_active=True).count(),
        "active_category_count": Category.objects.filter(is_active=True).count(),
        "active_document_type_count": DocumentType.objects.filter(is_active=True).count(),
        "latest_archives": latest_archives,
    }
    return render(request, "dashboard/home.html", context)
