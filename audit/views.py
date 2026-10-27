"""Consultation métier contrôlée du journal d’audit."""

import csv
from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from accounts.models import Role

from .models import AuditAction, AuditLog
from .presentation import ACTION_ICONS, ACTION_TONES, describe_details
from .services import record_audit_event


EXPORT_ROW_LIMIT = 50_000
# Préfixes interprétés comme formules par les tableurs (injection CSV).
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def can_view_audit(user) -> bool:
    return bool(
        user.is_authenticated
        and (user.is_superuser or user.role == Role.ADMINISTRATEUR)
    )


def _parse_date(value):
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def filtered_audit_queryset(params):
    """Applique les filtres communs à la liste et à l’export."""
    queryset = AuditLog.objects.select_related("actor", "archive")
    action = params.get("action", "").strip()
    query = params.get("q", "").strip()
    date_from = _parse_date(params.get("from", "").strip())
    date_to = _parse_date(params.get("to", "").strip())

    if action and action in AuditAction.values:
        queryset = queryset.filter(action=action)
    if query:
        queryset = queryset.filter(
            Q(actor_identifier__icontains=query)
            | Q(archive_reference__icontains=query)
            | Q(ip_address__icontains=query)
        )
    if date_from:
        queryset = queryset.filter(timestamp__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(timestamp__date__lte=date_to)
    return queryset.order_by("-timestamp", "-pk")


class AuditAccessMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not can_view_audit(request.user):
            raise PermissionDenied(
                "La consultation du journal d’audit est réservée aux administrateurs."
            )
        return super().dispatch(request, *args, **kwargs)


class AuditLogListView(AuditAccessMixin, ListView):
    """Affiche les événements d’audit aux seuls administrateurs autorisés."""

    model = AuditLog
    template_name = "audit/audit_log_list.html"
    context_object_name = "events"
    paginate_by = 25

    def get_queryset(self):
        return filtered_audit_queryset(self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parameters = self.request.GET.copy()
        parameters.pop("page", None)
        context["query_string"] = parameters.urlencode()
        context["has_active_search"] = any(value for value in parameters.values())
        context["action_filter"] = self.request.GET.get("action", "").strip()
        context["q_filter"] = self.request.GET.get("q", "").strip()
        context["from_filter"] = self.request.GET.get("from", "").strip()
        context["to_filter"] = self.request.GET.get("to", "").strip()
        context["available_actions"] = AuditAction.choices
        context["total_event_count"] = AuditLog.objects.count()
        context["result_count"] = context["paginator"].count
        if context.get("is_paginated"):
            context["page_links"] = list(
                context["paginator"].get_elided_page_range(
                    context["page_obj"].number, on_each_side=1, on_ends=1
                )
            )

        today = timezone.localdate()
        context["today_event_count"] = AuditLog.objects.filter(
            timestamp__date=today
        ).count()
        context["actor_count"] = (
            AuditLog.objects.values("actor_id").distinct().count()
        )
        context["action_breakdown"] = [
            {
                "action": row["action"],
                "label": AuditAction(row["action"]).label,
                "total": row["total"],
                "tone": ACTION_TONES.get(row["action"], "neutral"),
            }
            for row in AuditLog.objects.values("action")
            .annotate(total=Count("pk"))
            .order_by("-total")[:4]
        ]

        groups = []
        for event in context["events"]:
            event.tone = ACTION_TONES.get(event.action, "neutral")
            event.icon = ACTION_ICONS.get(event.action, "dot")
            event.detail_text = describe_details(event.details)
            day = timezone.localtime(event.timestamp).date()
            if not groups or groups[-1]["day"] != day:
                groups.append({"day": day, "events": []})
            groups[-1]["events"].append(event)
        context["event_groups"] = groups
        context["today"] = today
        context["yesterday"] = today - timedelta(days=1)
        return context


def _safe_cell(value) -> str:
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(FORMULA_PREFIXES) else text


class _Echo:
    def write(self, value):
        return value


class AuditLogExportView(AuditAccessMixin, View):
    """Exporte en CSV les événements filtrés ; l’export est lui-même journalisé."""

    def get(self, request, *args, **kwargs):
        queryset = filtered_audit_queryset(request.GET)[:EXPORT_ROW_LIMIT]
        row_count = queryset.count()
        record_audit_event(
            actor=request.user,
            action=AuditAction.AUDIT_EXPORT,
            request=request,
            details={"source": "web", "row_count": row_count},
        )

        writer = csv.writer(_Echo(), delimiter=";")

        def rows():
            yield "﻿"
            yield writer.writerow(
                ["horodatage", "utilisateur", "action", "archive", "adresse_ip"]
            )
            for event in queryset.iterator(chunk_size=2000):
                yield writer.writerow(
                    [
                        timezone.localtime(event.timestamp).isoformat(timespec="seconds"),
                        _safe_cell(event.actor_identifier),
                        event.get_action_display(),
                        _safe_cell(event.archive_reference),
                        event.ip_address or "",
                    ]
                )

        filename = f"journal-audit-{timezone.localdate():%Y%m%d}.csv"
        response = StreamingHttpResponse(rows(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Cache-Control"] = "private, no-store"
        return response
