"""Tonalités et icônes des actions d’audit, partagées par le journal et les fiches."""

from .models import AuditAction


ACTION_TONES = {
    AuditAction.LOGIN: "neutral",
    AuditAction.LOGOUT: "neutral",
    AuditAction.ARCHIVE_CREATE: "success",
    AuditAction.ARCHIVE_UPDATE: "info",
    AuditAction.ARCHIVE_VIEW: "muted",
    AuditAction.ARCHIVE_DOWNLOAD: "warning",
    AuditAction.ARCHIVE_PREVIEW: "muted",
    AuditAction.ARCHIVE_INTEGRITY_CHECK: "seal",
    AuditAction.AUDIT_EXPORT: "warning",
    AuditAction.PASSWORD_CHANGE: "info",
    AuditAction.ARCHIVE_EXPORT: "warning",
    AuditAction.TWO_FACTOR_ENABLE: "success",
    AuditAction.TWO_FACTOR_DISABLE: "warning",
    AuditAction.TWO_FACTOR_FAILURE: "warning",
    AuditAction.RECOVERY_CODE_USED: "warning",
}
ACTION_ICONS = {
    AuditAction.LOGIN: "login",
    AuditAction.LOGOUT: "logout",
    AuditAction.ARCHIVE_CREATE: "plus",
    AuditAction.ARCHIVE_UPDATE: "edit",
    AuditAction.ARCHIVE_VIEW: "eye",
    AuditAction.ARCHIVE_DOWNLOAD: "download",
    AuditAction.ARCHIVE_PREVIEW: "eye",
    AuditAction.ARCHIVE_INTEGRITY_CHECK: "seal",
    AuditAction.AUDIT_EXPORT: "export",
    AuditAction.PASSWORD_CHANGE: "key",
    AuditAction.ARCHIVE_EXPORT: "export",
    AuditAction.TWO_FACTOR_ENABLE: "shield",
    AuditAction.TWO_FACTOR_DISABLE: "unlock",
    AuditAction.TWO_FACTOR_FAILURE: "alert",
    AuditAction.RECOVERY_CODE_USED: "key",
}

INTEGRITY_RESULT_LABELS = {
    "VALID": "conforme",
    "MISMATCH": "empreinte divergente",
    "NO_FILE": "aucun fichier",
    "MISSING_CHECKSUM": "empreinte absente",
    "FILE_MISSING": "fichier introuvable",
    "ERROR": "erreur de lecture",
}


def describe_details(details) -> str:
    """Résumé lisible des détails minimaux autorisés par record_audit_event."""
    if not isinstance(details, dict):
        return ""
    parts = []
    if fields := details.get("changed_fields"):
        parts.append("Champs : " + ", ".join(fields))
    if result := details.get("result"):
        parts.append("Résultat : " + INTEGRITY_RESULT_LABELS.get(result, result))
    if "row_count" in details:
        count = details["row_count"]
        parts.append(f"{count} ligne{'s' if count > 1 else ''} exportée{'s' if count > 1 else ''}")
    return " · ".join(parts)
