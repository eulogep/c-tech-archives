"""API unique de création des événements d’audit métier."""

from __future__ import annotations

import ipaddress
from collections.abc import Mapping

from .models import AuditAction, AuditLog


ALLOWED_INTEGRITY_RESULTS = frozenset(
    {"VALID", "MISMATCH", "NO_FILE", "MISSING_CHECKSUM", "FILE_MISSING", "ERROR"}
)


def get_client_ip(request) -> str | None:
    """Retourne REMOTE_ADDR lorsqu’il est présent et syntaxiquement valide.

    Le MVP ne fait pas confiance à X-Forwarded-For. Une stratégie de proxy de
    confiance devra être validée séparément avec l’infrastructure C-Tech.
    """
    if request is None:
        return None
    address = request.META.get("REMOTE_ADDR")
    if not address:
        return None
    try:
        return str(ipaddress.ip_address(address))
    except ValueError:
        return None


def _minimal_details(details: Mapping | None) -> dict:
    """Conserve uniquement les métadonnées d’audit autorisées et non sensibles."""
    if not isinstance(details, Mapping):
        return {}

    sanitized: dict[str, object] = {}
    source = details.get("source")
    if isinstance(source, str) and len(source) <= 32:
        sanitized["source"] = source

    changed_fields = details.get("changed_fields")
    if isinstance(changed_fields, (list, tuple)):
        sanitized["changed_fields"] = [
            field
            for field in changed_fields
            if isinstance(field, str) and len(field) <= 64
        ]

    result = details.get("result")
    if isinstance(result, str) and result in ALLOWED_INTEGRITY_RESULTS:
        sanitized["result"] = result
    return sanitized


def record_audit_event(*, actor, action: str, request=None, archive=None, details=None) -> AuditLog:
    """Crée un événement métier structuré à partir de données minimales.

    Cette fonction est l’unique API applicative d’écriture. Toute erreur est
    propagée afin que le flux appelant puisse échouer proprement et ne prétende
    jamais qu’une action sensible est journalisée alors qu’elle ne l’est pas.
    """
    if action not in AuditAction.values:
        raise ValueError("Action d’audit non prise en charge.")
    if actor is None or not actor.is_authenticated:
        raise ValueError("Un acteur authentifié est requis pour l’audit.")

    return AuditLog.objects.create(
        actor=actor,
        actor_identifier=actor.get_username(),
        action=action,
        archive=archive,
        archive_reference=archive.reference if archive is not None else "",
        ip_address=get_client_ip(request),
        details=_minimal_details(details),
    )
