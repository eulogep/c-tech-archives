"""Indicateurs du tableau de bord, calculés sur le seul périmètre visible.

Chaque fonction reçoit un QuerySet déjà filtré par ``visible_archives_for`` :
aucune série ne peut refléter une archive que le rôle ne voit pas. Les
géométries SVG sont calculées ici pour que les gabarits restent déclaratifs et
compatibles avec une CSP sans style en ligne.
"""

from __future__ import annotations

import math
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone

from archives.models import ConfidentialityLevel
from archives.presentation import svg_number
from audit.models import AuditAction, AuditLog


MONTH_LABELS = (
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
)
DONUT_RADIUS = 40
DONUT_CIRCUMFERENCE = 2 * math.pi * DONUT_RADIUS
INTEGRITY_ALERT_RESULTS = ("MISMATCH", "FILE_MISSING", "ERROR")


def _month_start(moment):
    return moment.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _shift_month(moment, months):
    month_index = moment.month - 1 + months
    return moment.replace(year=moment.year + month_index // 12, month=month_index % 12 + 1)


def monthly_series(visible_archives, months=12):
    """Archives enregistrées par mois, du plus ancien au mois courant."""
    now = timezone.localtime()
    first = _shift_month(_month_start(now), -(months - 1))
    rows = (
        visible_archives.filter(created_at__gte=first)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Count("pk"))
    )
    totals = {(row["month"].year, row["month"].month): row["total"] for row in rows}
    points = []
    for index in range(months):
        month = _shift_month(first, index)
        points.append(
            {
                "label": MONTH_LABELS[month.month - 1],
                "year": month.year,
                "value": totals.get((month.year, month.month), 0),
            }
        )

    peak = max((point["value"] for point in points), default=0)
    chart_height, baseline, slot, bar_width = 104, 112, 30, 16
    for index, point in enumerate(points):
        height = (point["value"] / peak * chart_height) if peak else 0
        height = max(height, 2 if point["value"] else 0)
        point["x"] = svg_number(index * slot + (slot - bar_width) / 2)
        point["center"] = svg_number(index * slot + slot / 2)
        point["y"] = svg_number(baseline - height)
        point["label_y"] = svg_number(max(baseline - height - 4, 8))
        point["height"] = svg_number(height)
        point["width"] = bar_width
        point["is_current"] = index == months - 1

    # Courbe de tendance discrète, partagée avec la mini-courbe des indicateurs.
    spark = []
    for index, point in enumerate(points):
        x = index * (100 / (months - 1))
        y = 28 - (point["value"] / peak * 24 if peak else 0)
        spark.append(f"{x:.1f},{y:.1f}")
    return {
        "points": points,
        "peak": peak,
        "total": sum(point["value"] for point in points),
        "current": points[-1]["value"] if points else 0,
        "previous": points[-2]["value"] if len(points) > 1 else 0,
        "sparkline": " ".join(spark),
        "baseline": baseline,
    }


def confidentiality_donut(visible_archives, visible_levels):
    """Segments du anneau de confidentialité, limités aux niveaux visibles."""
    counts = visible_archives.aggregate(
        total=Count("pk"),
        **{
            value.lower(): Count("pk", filter=Q(confidentiality_level=value))
            for value in ConfidentialityLevel.values
        },
    )
    total = counts["total"] or 0
    segments = []
    offset = 0.0
    for value, label in ConfidentialityLevel.choices:
        if value not in visible_levels:
            continue
        count = counts[value.lower()]
        length = (count / total * DONUT_CIRCUMFERENCE) if total else 0
        segments.append(
            {
                "value": value.lower(),
                "label": label,
                "count": count,
                "percent": round(count / total * 100) if total else 0,
                "dasharray": f"{max(length - 1.5, 0):.2f} {DONUT_CIRCUMFERENCE:.2f}",
                "dashoffset": f"{-offset:.2f}",
            }
        )
        offset += length
    return {"total": total, "segments": segments, "radius": DONUT_RADIUS}


def top_services(visible_archives, limit=5):
    rows = list(
        visible_archives.values("service__name")
        .annotate(total=Count("pk"))
        .order_by("-total", "service__name")[:limit]
    )
    peak = rows[0]["total"] if rows else 0
    return [
        {
            "name": row["service__name"],
            "total": row["total"],
            "width": svg_number(row["total"] / peak * 100 if peak else 0),
        }
        for row in rows
    ]


def integrity_overview(visible_archives):
    """Couverture des empreintes et alertes récentes sur les archives visibles."""
    counts = visible_archives.aggregate(
        total=Count("pk"),
        sealed=Count("pk", filter=~Q(file="") & ~Q(checksum="")),
        unsealed=Count("pk", filter=~Q(file="") & Q(checksum="")),
        without_file=Count("pk", filter=Q(file="")),
    )
    total = counts["total"] or 0
    coverage = round(counts["sealed"] / total * 100) if total else 0
    circumference = 2 * math.pi * 52
    since = timezone.now() - timedelta(days=30)
    checks = AuditLog.objects.filter(
        action=AuditAction.ARCHIVE_INTEGRITY_CHECK,
        archive__in=visible_archives,
        timestamp__gte=since,
    )
    return {
        **counts,
        "coverage": coverage,
        "ring_dasharray": f"{circumference * coverage / 100:.2f} {circumference:.2f}",
        "checks_30d": checks.count(),
        "alerts_30d": checks.filter(details__result__in=INTEGRITY_ALERT_RESULTS).count(),
    }


def activity_heatmap(weeks=26):
    """Volume quotidien du journal d’audit, réservé aux profils autorisés."""
    today = timezone.localdate()
    start = today - timedelta(days=today.weekday() + 7 * (weeks - 1))
    rows = (
        AuditLog.objects.filter(timestamp__date__gte=start)
        .annotate(day=TruncDate("timestamp"))
        .values("day")
        .annotate(total=Count("pk"))
    )
    totals = {row["day"]: row["total"] for row in rows}
    peak = max(totals.values(), default=0)
    cell, gap, left, top = 11, 3, 16, 14
    cells = []
    months = []
    for week in range(weeks):
        week_start = start + timedelta(days=week * 7)
        x = left + week * (cell + gap)
        if week == 0 or week_start.month != (week_start - timedelta(days=7)).month:
            if week < weeks - 2:
                months.append({"x": x, "label": MONTH_LABELS[week_start.month - 1]})
        for weekday in range(7):
            day = week_start + timedelta(days=weekday)
            if day > today:
                continue
            value = totals.get(day, 0)
            level = 0 if not value or not peak else min(4, math.ceil(value / peak * 4))
            cells.append(
                {
                    "x": x,
                    "y": top + weekday * (cell + gap),
                    "level": level,
                    "value": value,
                    "day": day,
                }
            )
    weekdays = [
        {"y": top + index * (cell + gap) + cell - 2, "label": label}
        for index, label in ((0, "L"), (2, "M"), (4, "V"))
    ]
    return {
        "cells": cells,
        "months": months,
        "weekdays": weekdays,
        "month_y": top - 4,
        "width": left + weeks * (cell + gap) - gap,
        "height": top + 7 * (cell + gap) - gap,
        "cell": cell,
        "weeks": weeks,
        "total": sum(totals.values()),
        "peak": peak,
        "active_days": sum(1 for value in totals.values() if value),
    }


def action_breakdown(days=30, limit=5):
    """Actions les plus fréquentes du journal sur la période récente."""
    since = timezone.now() - timedelta(days=days)
    rows = list(
        AuditLog.objects.filter(timestamp__gte=since)
        .values("action")
        .annotate(total=Count("pk"))
        .order_by("-total", "action")[:limit]
    )
    peak = rows[0]["total"] if rows else 0
    return [
        {
            "label": AuditAction(row["action"]).label,
            "total": row["total"],
            "width": svg_number(row["total"] / peak * 100 if peak else 0),
        }
        for row in rows
    ]


def greeting_for(moment=None):
    hour = (moment or timezone.localtime()).hour
    if 5 <= hour < 12:
        return "Bonjour"
    if 12 <= hour < 18:
        return "Bon après-midi"
    return "Bonsoir"
