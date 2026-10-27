"""Circuit de validation des archives et visa signé.

Règles :
- seule une personne autorisée à modifier l’archive peut demander sa
  validation, à un administrateur actif qui la voit ;
- personne ne valide sa propre demande (contrainte en base également) ;
- seul le valideur désigné décide ; la décision est journalisée ;
- le visa d’une validation est un HMAC-SHA256 sur la décision et sur une
  empreinte de l’archive (métadonnées et SHA-256 du fichier) au moment de la
  décision. Si l’archive change ensuite, le visa est signalé comme dépassé ;
  si le visa lui-même est altéré en base, il est signalé comme invalide.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import salted_hmac

from accounts.models import Role
from audit.models import AuditAction
from audit.services import record_audit_event

from .models import ApprovalRequest, ApprovalStatus, Archive
from .permissions import can_update_archive, can_view_archive


VISA_SALT = "ctech.approval-visa"


@dataclass(frozen=True)
class VisaState:
    tone: str
    label: str
    detail: str


def archive_fingerprint(archive: Archive) -> str:
    """Empreinte canonique de ce que le valideur a approuvé."""
    payload = {
        "reference": archive.reference,
        "title": archive.title,
        "description": archive.description,
        "document_date": archive.document_date.isoformat() if archive.document_date else "",
        "confidentiality_level": archive.confidentiality_level,
        "service": archive.service_id,
        "category": archive.category_id,
        "document_type": archive.document_type_id,
        "checksum": archive.checksum,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _visa_payload(approval: ApprovalRequest) -> str:
    return "|".join(
        (
            str(approval.pk),
            str(approval.archive_id),
            str(approval.requested_by_id),
            str(approval.approver_id),
            approval.status,
            approval.decided_at.isoformat() if approval.decided_at else "",
            approval.signed_fingerprint,
        )
    )


def _sign(approval: ApprovalRequest) -> str:
    return salted_hmac(VISA_SALT, _visa_payload(approval), algorithm="sha256").hexdigest()


def is_approver_role(user) -> bool:
    return bool(user.is_active and (user.is_superuser or user.role == Role.ADMINISTRATEUR))


def eligible_approvers(user, archive: Archive):
    """Administrateurs actifs, autres que le demandeur, capables de voir l’archive."""
    candidates = (
        get_user_model()
        .objects.filter(is_active=True)
        .filter(Q(role=Role.ADMINISTRATEUR) | Q(is_superuser=True))
        .exclude(pk=user.pk)
        .defer("profile_avatar")
        .order_by("last_name", "first_name", "email")
    )
    return [candidate for candidate in candidates if can_view_archive(candidate, archive)]


def pending_approval(archive: Archive):
    return archive.approvals.filter(status=ApprovalStatus.PENDING).first()


def can_request_approval(user, archive: Archive) -> bool:
    return can_update_archive(user, archive) and pending_approval(archive) is None


def can_decide(user, approval: ApprovalRequest) -> bool:
    return (
        approval.status == ApprovalStatus.PENDING
        and approval.approver_id == user.pk
        and approval.requested_by_id != user.pk
        and is_approver_role(user)
        and can_view_archive(user, approval.archive)
    )


def request_approval(*, user, archive: Archive, approver, message: str, request=None) -> ApprovalRequest:
    with transaction.atomic():
        approval = ApprovalRequest.objects.create(
            archive=archive, requested_by=user, approver=approver, message=message.strip()
        )
        record_audit_event(
            actor=user,
            action=AuditAction.APPROVAL_REQUEST,
            request=request,
            archive=archive,
            details={"source": "web"},
        )
    return approval


def decide(*, user, approval: ApprovalRequest, approve: bool, comment: str, request=None) -> ApprovalRequest:
    with transaction.atomic():
        approval.status = ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED
        approval.decision_comment = comment.strip()
        approval.decided_at = timezone.now()
        approval.signed_fingerprint = archive_fingerprint(approval.archive)
        approval.signature = _sign(approval)
        approval.save(
            update_fields=[
                "status",
                "decision_comment",
                "decided_at",
                "signed_fingerprint",
                "signature",
            ]
        )
        record_audit_event(
            actor=user,
            action=AuditAction.APPROVAL_GRANT if approve else AuditAction.APPROVAL_REJECT,
            request=request,
            archive=approval.archive,
            details={"source": "web"},
        )
    return approval


def verify_visa(approval: ApprovalRequest) -> VisaState:
    """Contrôle le visa d’une validation par rapport à l’archive actuelle."""
    if approval.status != ApprovalStatus.APPROVED:
        return VisaState("unknown", "Aucun visa", "Seule une validation accordée porte un visa.")
    if not approval.signature or not hmac.compare_digest(approval.signature, _sign(approval)):
        return VisaState(
            "alert",
            "Visa invalide",
            "La signature ne correspond plus à la décision enregistrée : le registre a été altéré.",
        )
    if approval.signed_fingerprint != archive_fingerprint(approval.archive):
        return VisaState(
            "warning",
            "Visa dépassé",
            "L’archive a été modifiée depuis sa validation : une nouvelle validation est nécessaire.",
        )
    return VisaState(
        "valid",
        "Visa valide",
        "L’archive est identique à la version validée (métadonnées et empreinte du fichier).",
    )
