"""Vue de synthèse authentifiée du domaine documentaire."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from archives.models import ArchiveStatus, Category, DocumentType, Service
from archives.permissions import visible_archives_for
from audit.context_processors import audit_policy
from audit.models import AuditLog


@login_required
def home(request):
    """Affiche des indicateurs agrégés limités au périmètre visible du rôle.

    Le RBAC filtre déjà les archives avant tout compteur. Le dashboard
    ne retourne aucune métadonnée individuelle et n’infère aucun niveau masqué.
    """
    visible_archives = visible_archives_for(request.user)
    can_view_audit = audit_policy(request)["audit_policy"]["can_view"]
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
        "recent_archives": visible_archives.select_related(
            "service", "category", "document_type"
        ).order_by("-created_at", "-pk")[:5],
    }
    if can_view_audit:
        context["recent_audit_events"] = AuditLog.objects.select_related(
            "actor", "archive"
        ).order_by("-timestamp", "-pk")[:5]
    return render(request, "dashboard/home.html", context)
