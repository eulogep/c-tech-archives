"""Calendrier de conservation : états, échéances et filtres.

Deux dates optionnelles portent le cycle de vie d’un dossier : la prochaine
révision (relire, mettre à jour) et la fin de conservation, c’est-à-dire la
fin de la durée d’utilité administrative (DUA) après laquelle il faut décider
du sort du dossier : élimination contrôlée ou versement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Q, QuerySet
from django.utils import timezone


DUE_SOON_DAYS = 90
REVIEW_SOON_DAYS = 30

DEADLINE_FILTERS = {
    "overdue": "Échéance dépassée",
    "next_30": "Dans les 30 jours",
    "next_90": "Dans les 90 jours",
    "undefined": "Sans échéance",
}

# Durées usuelles proposées dans le formulaire (en années) ; la règle exacte
# dépend du tableau de gestion de C-Tech.
RETENTION_PRESETS = (1, 5, 10, 30)


@dataclass(frozen=True)
class RetentionState:
    tone: str
    label: str
    detail: str
    progress: int | None = None


def _days_label(days: int) -> str:
    if days == 0:
        return "aujourd’hui"
    if days > 0:
        return f"dans {days} jour{'s' if days > 1 else ''}"
    days = -days
    return f"depuis {days} jour{'s' if days > 1 else ''}"


def retention_state(archive, today: date | None = None) -> RetentionState:
    """Synthèse de l’état de conservation affichée sur la fiche et les listes."""
    today = today or timezone.localdate()
    end = archive.retention_until
    review = archive.review_date
    start = archive.document_date or timezone.localtime(archive.created_at).date()

    progress = None
    if end:
        total = max((end - start).days, 1)
        progress = max(0, min(100, round((today - start).days / total * 100)))

    if end and end < today:
        return RetentionState(
            "alert",
            "Conservation échue",
            f"Fin de conservation {_days_label((end - today).days)} : décider du sort du dossier.",
            progress,
        )
    if review and review < today:
        return RetentionState(
            "warning",
            "Révision en retard",
            f"Révision prévue le {review:%d/%m/%Y}, {_days_label((review - today).days)}.",
            progress,
        )
    if end and (end - today).days <= DUE_SOON_DAYS:
        return RetentionState(
            "warning",
            "Fin de conservation proche",
            f"Fin de conservation {_days_label((end - today).days)}.",
            progress,
        )
    if review and (review - today).days <= REVIEW_SOON_DAYS:
        return RetentionState(
            "info",
            "Révision à prévoir",
            f"Révision {_days_label((review - today).days)}.",
            progress,
        )
    if end or review:
        return RetentionState(
            "valid",
            "Dans les délais",
            f"Conservé jusqu’au {end:%d/%m/%Y}." if end else f"Prochaine révision le {review:%d/%m/%Y}.",
            progress,
        )
    return RetentionState(
        "unknown",
        "Aucune échéance",
        "Aucune date de révision ni de fin de conservation n’est renseignée.",
        None,
    )


def filter_by_deadline(queryset: QuerySet, key: str, today: date | None = None) -> QuerySet:
    """Restreint un QuerySet déjà filtré par le RBAC selon une échéance."""
    today = today or timezone.localdate()
    if key == "overdue":
        return queryset.filter(Q(retention_until__lt=today) | Q(review_date__lt=today))
    if key in {"next_30", "next_90"}:
        horizon = today + timedelta(days=30 if key == "next_30" else 90)
        return queryset.filter(
            Q(retention_until__range=(today, horizon)) | Q(review_date__range=(today, horizon))
        )
    if key == "undefined":
        return queryset.filter(retention_until__isnull=True, review_date__isnull=True)
    return queryset


def deadline_overview(visible_archives: QuerySet, today: date | None = None, limit: int = 5):
    """Compteurs et prochaines échéances du périmètre visible (tableau de bord)."""
    today = today or timezone.localdate()
    upcoming = []
    horizon = today + timedelta(days=DUE_SOON_DAYS)
    candidates = (
        filter_by_deadline(visible_archives, "overdue", today)
        | visible_archives.filter(
            Q(retention_until__range=(today, horizon)) | Q(review_date__range=(today, horizon))
        )
    ).distinct()
    for archive in candidates.only(
        "pk", "reference", "title", "retention_until", "review_date", "confidentiality_level"
    ):
        events = []
        if archive.retention_until and archive.retention_until <= horizon:
            events.append((archive.retention_until, "Fin de conservation"))
        if archive.review_date and archive.review_date <= horizon:
            events.append((archive.review_date, "Révision"))
        when, kind = min(events)
        upcoming.append(
            {
                "archive": archive,
                "date": when,
                "kind": kind,
                "days": (when - today).days,
                "overdue": when < today,
            }
        )
    upcoming.sort(key=lambda item: item["date"])
    return {
        "overdue": filter_by_deadline(visible_archives, "overdue", today).count(),
        "next_30": filter_by_deadline(visible_archives, "next_30", today).count(),
        "next_90": filter_by_deadline(visible_archives, "next_90", today).count(),
        "undefined": filter_by_deadline(visible_archives, "undefined", today).count(),
        "upcoming": upcoming[:limit],
    }
