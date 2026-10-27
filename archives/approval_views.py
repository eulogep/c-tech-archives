"""Vues du circuit de validation : demande, décision et file de travail."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from .approvals import (
    can_decide,
    can_request_approval,
    decide,
    eligible_approvers,
    pending_approval,
    request_approval,
    verify_visa,
)
from .models import ApprovalRequest, ApprovalStatus
from .permissions import can_update_archive, has_archive_access, visible_archives_for


def _visible_archive(user, pk):
    if not has_archive_access(user):
        raise PermissionDenied("Ce compte ne possède aucun accès métier aux archives.")
    return get_object_or_404(visible_archives_for(user), pk=pk)


@login_required
@require_POST
def approval_request(request, pk):
    archive = _visible_archive(request.user, pk)
    if not can_update_archive(request.user, archive):
        raise PermissionDenied("Seul un profil autorisé à modifier l’archive peut demander sa validation.")
    if not can_request_approval(request.user, archive):
        messages.info(request, "Une validation est déjà en attente pour cette archive.")
        return redirect("archives:detail", pk=archive.pk)

    approvers = {str(user.pk): user for user in eligible_approvers(request.user, archive)}
    approver = approvers.get(request.POST.get("approver", ""))
    if approver is None:
        messages.error(request, "Choisissez un administrateur valideur autre que vous-même.")
        return redirect("archives:detail", pk=archive.pk)
    request_approval(
        user=request.user,
        archive=archive,
        approver=approver,
        message=request.POST.get("message", "")[:1000],
        request=request,
    )
    messages.success(
        request, f"Validation demandée à {approver.get_full_name() or approver.email}."
    )
    return redirect("archives:detail", pk=archive.pk)


@login_required
@require_POST
def approval_decide(request, approval_id):
    if not has_archive_access(request.user):
        raise PermissionDenied("Ce compte ne possède aucun accès métier aux archives.")
    approval = get_object_or_404(
        ApprovalRequest.objects.select_related("archive"),
        pk=approval_id,
        archive__in=visible_archives_for(request.user),
    )
    if not can_decide(request.user, approval):
        raise PermissionDenied("Seul le valideur désigné peut décider de cette demande.")
    decision = request.POST.get("decision")
    comment = request.POST.get("comment", "")[:1000]
    if decision not in {"approve", "reject"}:
        messages.error(request, "Décision inconnue.")
    elif decision == "reject" and not comment.strip():
        messages.error(request, "Un refus doit être motivé par un commentaire.")
    else:
        decide(user=request.user, approval=approval, approve=decision == "approve", comment=comment, request=request)
        messages.success(
            request,
            "Archive validée : son visa est signé." if decision == "approve" else "Validation refusée.",
        )
    target = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = ""
    return redirect(target or "archives:approvals")


@login_required
@require_GET
def approval_queue(request):
    if not has_archive_access(request.user):
        raise PermissionDenied("Ce compte ne possède aucun accès métier aux archives.")
    visible = visible_archives_for(request.user)
    base = ApprovalRequest.objects.filter(archive__in=visible).select_related(
        "archive", "requested_by", "approver"
    )
    to_review = list(base.filter(approver=request.user, status=ApprovalStatus.PENDING))
    decided = list(base.filter(approver=request.user).exclude(status=ApprovalStatus.PENDING)[:15])
    for approval in decided:
        approval.visa = verify_visa(approval)
    return render(
        request,
        "archives/approval_queue.html",
        {
            "to_review": to_review,
            "my_requests": base.filter(requested_by=request.user)[:15],
            "decided": decided,
        },
    )


def approval_context(user, archive):
    """Contexte de la section « F. Validation et visa » de la fiche."""
    approvals = list(archive.approvals.select_related("requested_by", "approver")[:6])
    latest_approved = next((a for a in approvals if a.status == ApprovalStatus.APPROVED), None)
    pending = pending_approval(archive)
    # Le détail (personnes, commentaires) est réservé aux profils qui gèrent l’archive.
    show_details = can_update_archive(user, archive) or (pending and pending.approver_id == user.pk)
    context = {
        "approvals": approvals if show_details else [],
        "approval_details_visible": show_details,
        "approval_pending": pending,
        "approval_can_decide": bool(pending and can_decide(user, pending)),
        "approval_can_request": can_request_approval(user, archive),
        "approval_visa": verify_visa(latest_approved) if latest_approved else None,
        "approval_latest": latest_approved,
    }
    if context["approval_can_request"]:
        context["approval_candidates"] = eligible_approvers(user, archive)
    return context
