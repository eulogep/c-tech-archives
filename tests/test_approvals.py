"""Tests du circuit de validation et du visa signé."""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role
from archives.approvals import decide, request_approval, verify_visa
from archives.models import (
    ApprovalRequest,
    ApprovalStatus,
    Archive,
    ArchiveStatus,
    Category,
    ConfidentialityLevel,
    DocumentType,
    Service,
)
from audit.models import AuditAction, AuditLog


PASSWORD = "Synthetic-Approval-Password-2026!"


class ApprovalTestCase(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.admin = users.create_user(
            username="appr-admin@example.test", email="appr-admin@example.test",
            password=PASSWORD, role=Role.ADMINISTRATEUR, first_name="Ada", last_name="Valideuse",
        )
        self.second_admin = users.create_user(
            username="appr-admin2@example.test", email="appr-admin2@example.test",
            password=PASSWORD, role=Role.ADMINISTRATEUR,
        )
        self.agent = users.create_user(
            username="appr-agent@example.test", email="appr-agent@example.test",
            password=PASSWORD, role=Role.AGENT_ARCHIVES,
        )
        self.consultant = users.create_user(
            username="appr-consultant@example.test", email="appr-consultant@example.test",
            password=PASSWORD, role=Role.CONSULTANT,
        )
        self.archive = Archive.objects.create(
            reference="CT-APPR-001",
            title="Contrat à valider",
            category=Category.objects.create(name="Catégorie validation"),
            document_type=DocumentType.objects.create(name="Type validation"),
            service=Service.objects.create(name="Service validation"),
            uploaded_by=self.agent,
            status=ArchiveStatus.ACTIVE,
            confidentiality_level=ConfidentialityLevel.INTERNAL,
            checksum="b" * 64,
        )

    def request_as(self, user, approver, message="Merci"):
        self.client.force_login(user)
        return self.client.post(
            reverse("archives:approval_request", args=[self.archive.pk]),
            {"approver": approver.pk, "message": message},
        )

    def decide_as(self, user, approval, decision, comment=""):
        self.client.force_login(user)
        return self.client.post(
            reverse("archives:approval_decide", args=[approval.pk]),
            {"decision": decision, "comment": comment},
        )


class ApprovalWorkflowTests(ApprovalTestCase):
    def test_agent_requests_and_designated_admin_approves(self):
        self.request_as(self.agent, self.admin)
        approval = ApprovalRequest.objects.get()

        self.assertEqual(approval.status, ApprovalStatus.PENDING)
        self.client.force_login(self.admin)
        queue = self.client.get(reverse("archives:approvals"))
        self.assertEqual([a.pk for a in queue.context["to_review"]], [approval.pk])
        self.assertEqual(queue.context["pending_approvals_count"], 1)

        self.decide_as(self.admin, approval, "approve", "Conforme")
        approval.refresh_from_db()
        self.assertEqual(approval.status, ApprovalStatus.APPROVED)
        self.assertEqual(verify_visa(approval).tone, "valid")
        self.assertEqual(
            set(AuditLog.objects.filter(archive=self.archive).values_list("action", flat=True)),
            {AuditAction.APPROVAL_REQUEST, AuditAction.APPROVAL_GRANT},
        )

    def test_consultant_can_neither_request_nor_decide(self):
        self.assertEqual(self.request_as(self.consultant, self.admin).status_code, 404)
        approval = request_approval(user=self.agent, archive=self.archive, approver=self.admin, message="")
        self.assertEqual(self.decide_as(self.consultant, approval, "approve").status_code, 404)

    def test_self_approval_is_impossible(self):
        self.request_as(self.admin, self.admin)
        self.assertFalse(ApprovalRequest.objects.exists())

        with self.assertRaises(IntegrityError), transaction.atomic():
            ApprovalRequest.objects.create(
                archive=self.archive, requested_by=self.admin, approver=self.admin
            )

    def test_only_the_designated_approver_decides(self):
        approval = request_approval(user=self.agent, archive=self.archive, approver=self.admin, message="")

        self.assertEqual(self.decide_as(self.second_admin, approval, "approve").status_code, 403)
        approval.refresh_from_db()
        self.assertEqual(approval.status, ApprovalStatus.PENDING)

    def test_a_single_pending_request_per_archive(self):
        self.request_as(self.agent, self.admin)
        self.request_as(self.agent, self.second_admin)

        self.assertEqual(ApprovalRequest.objects.filter(status=ApprovalStatus.PENDING).count(), 1)

    def test_rejection_requires_a_comment_and_allows_a_new_request(self):
        approval = request_approval(user=self.agent, archive=self.archive, approver=self.admin, message="")

        self.decide_as(self.admin, approval, "reject")
        approval.refresh_from_db()
        self.assertEqual(approval.status, ApprovalStatus.PENDING)

        self.decide_as(self.admin, approval, "reject", "Annexe manquante")
        approval.refresh_from_db()
        self.assertEqual(approval.status, ApprovalStatus.REJECTED)
        self.request_as(self.agent, self.admin)
        self.assertEqual(ApprovalRequest.objects.filter(status=ApprovalStatus.PENDING).count(), 1)


class VisaTests(ApprovalTestCase):
    def setUp(self):
        super().setUp()
        self.approval = request_approval(user=self.agent, archive=self.archive, approver=self.admin, message="")
        decide(user=self.admin, approval=self.approval, approve=True, comment="OK")

    def test_visa_detects_later_changes_to_the_archive(self):
        Archive.objects.filter(pk=self.archive.pk).update(title="Titre modifié après validation")
        self.approval.refresh_from_db()

        self.assertEqual(verify_visa(self.approval).tone, "warning")

    def test_visa_detects_tampering_with_the_decision(self):
        ApprovalRequest.objects.filter(pk=self.approval.pk).update(approver=self.second_admin)
        self.approval.refresh_from_db()

        self.assertEqual(verify_visa(self.approval).tone, "alert")

    def test_detail_shows_visa_and_hides_people_from_consultants(self):
        Archive.objects.filter(pk=self.archive.pk).update(
            confidentiality_level=ConfidentialityLevel.PUBLIC
        )
        self.client.force_login(self.consultant)
        consultant = self.client.get(reverse("archives:detail", args=[self.archive.pk]))
        self.client.force_login(self.agent)
        agent = self.client.get(reverse("archives:detail", args=[self.archive.pk]))

        self.assertContains(consultant, "F. Validation et visa")
        self.assertNotContains(consultant, self.admin.email)
        self.assertNotContains(consultant, "Demander une validation")
        self.assertContains(agent, "Ada Valideuse")
        self.assertNotContains(consultant, "Modifier")
