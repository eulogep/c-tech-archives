"""Vue de synthèse authentifiée du domaine documentaire."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from archives.models import ArchiveStatus, Category, DocumentType, Service
from archives.permissions import visible_archives_for, visible_confidentiality_levels_for
from archives.retention import deadline_overview
from audit.context_processors import audit_policy
from audit.models import AuditLog

from . import analytics


@login_required
def home(request):
    """Affiche des indicateurs agrégés limités au périmètre visible du rôle.

    Le RBAC filtre déjà les archives avant tout compteur. Le dashboard
    ne retourne aucune métadonnée individuelle et n’infère aucun niveau masqué.
    """
    visible_archives = visible_archives_for(request.user)
    visible_levels = visible_confidentiality_levels_for(request.user)
    can_view_audit = audit_policy(request)["audit_policy"]["can_view"]
    monthly = analytics.monthly_series(visible_archives)
    context = {
        "greeting": analytics.greeting_for(),
        "today": timezone.localdate(),
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
        "monthly": monthly,
        "donut": analytics.confidentiality_donut(visible_archives, visible_levels),
        "services_ranking": analytics.top_services(visible_archives),
        "integrity": analytics.integrity_overview(visible_archives),
        "deadlines": deadline_overview(visible_archives),
    }
    if can_view_audit:
        context["recent_audit_events"] = AuditLog.objects.select_related(
            "actor", "archive"
        ).order_by("-timestamp", "-pk")[:6]
        context["heatmap"] = analytics.activity_heatmap()
        context["action_ranking"] = analytics.action_breakdown()
    return render(request, "dashboard/home.html", context)


@login_required
def report(request):
    """Rapport d’activité imprimable, limité au périmètre visible du rôle."""
    try:
        days = int(request.GET.get("days", 30))
    except ValueError:
        days = 30
    visible_archives = visible_archives_for(request.user)
    can_view_audit = audit_policy(request)["audit_policy"]["can_view"]
    context = {
        "report": analytics.activity_report(visible_archives, days, can_view_audit),
        "periods": analytics.REPORT_PERIODS,
        "deadlines": deadline_overview(visible_archives),
        "generated_at": timezone.localtime(),
    }
    return render(request, "dashboard/report.html", context)
