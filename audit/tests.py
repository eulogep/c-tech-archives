"""Tests du journal d’audit append-only T-012."""

from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from accounts.models import Role
from archives.models import (
    Archive,
    ArchiveStatus,
    Category,
    ConfidentialityLevel,
    DocumentType,
    Service,
)

from .models import AuditAction, AuditLog


class AuditLogTests(TestCase):
    """Matrice AUDIT-001 à AUDIT-030 sur les actions métier sensibles."""

    PDF_CONTENT = b"%PDF-1.4\nsynthetic audit test document\n"
    PASSWORD = "TresSecret-2026"

    def setUp(self):
        self.private_media = TemporaryDirectory()
        self.settings_override = override_settings(PRIVATE_MEDIA_ROOT=self.private_media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.private_media.cleanup)

        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username="audit-admin",
            email="audit-admin@example.test",
            password=self.PASSWORD,
            role=Role.ADMINISTRATEUR,
        )
        self.agent = user_model.objects.create_user(
            username="audit-agent",
            email="audit-agent@example.test",
            password="MotDePasse-AuditAgent-2026",
            role=Role.AGENT_ARCHIVES,
        )
        self.consultant = user_model.objects.create_user(
            username="audit-consultant",
            email="audit-consultant@example.test",
            password="MotDePasse-AuditConsultant-2026",
            role=Role.CONSULTANT,
        )
        self.superuser = user_model.objects.create_superuser(
            username="audit-superuser",
            email="audit-superuser@example.test",
            password="MotDePasse-AuditSuperuser-2026",
        )
        self.service = Service.objects.create(name="Service audit")
        self.category = Category.objects.create(name="Catégorie audit")
        self.document_type = DocumentType.objects.create(name="Type audit")
        self.create_url = "/archives/new/"
        self.audit_url = "/audit/"

    def create_archive(self, confidentiality_level=ConfidentialityLevel.PUBLIC, index=1):
        return Archive.objects.create(
            reference=f"CT-AUDIT-{index:05d}",
            title=f"Archive audit {index}",
            description="Archive synthétique destinée aux tests d’audit",
            category=self.category,
            document_type=self.document_type,
            service=self.service,
            uploaded_by=self.admin,
            status=ArchiveStatus.ACTIVE,
            confidentiality_level=confidentiality_level,
            file=SimpleUploadedFile(
                f"audit-{index}.pdf", self.PDF_CONTENT, content_type="application/pdf"
            ),
            file_size=len(self.PDF_CONTENT),
        )

    def archive_payload(self, reference, confidentiality_level=ConfidentialityLevel.PUBLIC, **overrides):
        data = {
            "reference": reference,
            "title": "Archive créée dans le test d’audit",
            "description": "Création synthétique pour journalisation",
            "category": str(self.category.pk),
            "document_type": str(self.document_type.pk),
            "service": str(self.service.pk),
            "document_date": "2026-08-14",
            "status": ArchiveStatus.ACTIVE,
            "confidentiality_level": confidentiality_level,
        }
        data.update(overrides)
        return data

    def audit_events(self, action, archive=None):
        queryset = AuditLog.objects.filter(action=action)
        if archive is not None:
            queryset = queryset.filter(archive=archive)
        return queryset

    def test_audit_001_successful_login_creates_login_event(self):
        self.assertTrue(self.client.login(username=self.admin.username, password=self.PASSWORD))

        event = self.audit_events(AuditAction.LOGIN).get()

        self.assertEqual(event.actor, self.admin)
        self.assertEqual(event.actor_identifier, self.admin.username)

    def test_audit_002_logout_creates_logout_event(self):
        self.client.login(username=self.admin.username, password=self.PASSWORD)

        response = self.client.post("/accounts/logout/")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.audit_events(AuditAction.LOGOUT).filter(actor=self.admin).exists())

    def test_audit_003_password_is_never_stored_in_login_details(self):
        self.client.login(username=self.admin.username, password=self.PASSWORD)

        event = self.audit_events(AuditAction.LOGIN).get()

        self.assertNotIn(self.PASSWORD, str(event.details))
        self.assertNotIn("password", event.details)

    def test_audit_004_successful_archive_creation_creates_event(self):
        self.client.force_login(self.agent)

        response = self.client.post(
            self.create_url, self.archive_payload("CT-AUDIT-CREATE-004")
        )

        archive = Archive.objects.get(reference="CT-AUDIT-CREATE-004")
        event = self.audit_events(AuditAction.ARCHIVE_CREATE, archive).get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(event.actor, self.agent)

    def test_audit_005_invalid_creation_creates_no_create_event(self):
        self.client.force_login(self.agent)

        response = self.client.post(
            self.create_url, self.archive_payload("", title=""),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.audit_events(AuditAction.ARCHIVE_CREATE).exists())

    def test_audit_006_successful_update_creates_event(self):
        archive = self.create_archive()
        self.client.force_login(self.agent)

        response = self.client.post(
            f"/archives/{archive.pk}/edit/",
            self.archive_payload(
                archive.reference, title="Archive audit modifiée"
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.audit_events(AuditAction.ARCHIVE_UPDATE, archive).exists())

    def test_audit_007_rbac_refused_update_creates_no_update_event(self):
        archive = self.create_archive()
        self.client.force_login(self.consultant)

        response = self.client.post(
            f"/archives/{archive.pk}/edit/",
            self.archive_payload(archive.reference),
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.audit_events(AuditAction.ARCHIVE_UPDATE, archive).exists())

    def test_audit_008_update_details_contain_only_changed_field_names(self):
        archive = self.create_archive()
        self.client.force_login(self.agent)

        self.client.post(
            f"/archives/{archive.pk}/edit/",
            self.archive_payload(
                archive.reference,
                title="Nouveau titre audit",
                description=archive.description,
                document_date="",
                status=ArchiveStatus.ARCHIVED,
            ),
        )

        event = self.audit_events(AuditAction.ARCHIVE_UPDATE, archive).get()
        self.assertEqual(set(event.details["changed_fields"]), {"title", "status"})
        self.assertEqual(set(event.details), {"changed_fields", "source"})

    def test_audit_009_authorized_detail_creates_view_event(self):
        archive = self.create_archive()
        self.client.force_login(self.consultant)

        response = self.client.get(f"/archives/{archive.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.audit_events(AuditAction.ARCHIVE_VIEW, archive).exists())

    def test_audit_010_forbidden_detail_creates_no_view_event(self):
        archive = self.create_archive(ConfidentialityLevel.INTERNAL)
        self.client.force_login(self.consultant)

        response = self.client.get(f"/archives/{archive.pk}/")

        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.audit_events(AuditAction.ARCHIVE_VIEW, archive).exists())

    def test_audit_011_successful_download_creates_event(self):
        archive = self.create_archive()
        self.client.force_login(self.consultant)

        response = self.client.get(f"/archives/{archive.pk}/download/")
        b"".join(response.streaming_content)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.audit_events(AuditAction.ARCHIVE_DOWNLOAD, archive).exists())

    def test_audit_012_forbidden_download_creates_no_event(self):
        archive = self.create_archive(ConfidentialityLevel.INTERNAL)
        self.client.force_login(self.consultant)

        response = self.client.get(f"/archives/{archive.pk}/download/")

        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.audit_events(AuditAction.ARCHIVE_DOWNLOAD, archive).exists())

    def test_audit_013_missing_downloaded_file_creates_no_success_event(self):
        archive = self.create_archive()
        archive.file.storage.delete(archive.file.name)
        self.client.force_login(self.consultant)

        response = self.client.get(f"/archives/{archive.pk}/download/")

        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.audit_events(AuditAction.ARCHIVE_DOWNLOAD, archive).exists())

    def test_audit_014_remote_addr_is_recorded(self):
        archive = self.create_archive()
        self.client.force_login(self.consultant)

        self.client.get(f"/archives/{archive.pk}/", REMOTE_ADDR="198.51.100.42")

        event = self.audit_events(AuditAction.ARCHIVE_VIEW, archive).get()
        self.assertEqual(event.ip_address, "198.51.100.42")

    def test_audit_015_missing_ip_is_handled(self):
        archive = self.create_archive()
        self.client.force_login(self.consultant)

        self.client.get(f"/archives/{archive.pk}/", REMOTE_ADDR="")

        event = self.audit_events(AuditAction.ARCHIVE_VIEW, archive).get()
        self.assertIsNone(event.ip_address)

    def test_audit_016_timestamp_is_generated_by_the_server(self):
        before = timezone.now()
        self.client.login(username=self.admin.username, password=self.PASSWORD)
        after = timezone.now()

        event = self.audit_events(AuditAction.LOGIN).get()
        self.assertGreaterEqual(event.timestamp, before)
        self.assertLessEqual(event.timestamp, after)

    def test_audit_017_event_actor_is_correct(self):
        self.client.force_login(self.agent)

        self.client.post(self.create_url, self.archive_payload("CT-AUDIT-ACTOR-017"))

        event = self.audit_events(AuditAction.ARCHIVE_CREATE).get()
        self.assertEqual(event.actor, self.agent)

    def test_audit_018_event_archive_is_correct(self):
        self.client.force_login(self.agent)

        self.client.post(self.create_url, self.archive_payload("CT-AUDIT-ARCHIVE-018"))

        archive = Archive.objects.get(reference="CT-AUDIT-ARCHIVE-018")
        event = self.audit_events(AuditAction.ARCHIVE_CREATE).get()
        self.assertEqual(event.archive, archive)
        self.assertEqual(event.archive_reference, archive.reference)

    def test_audit_019_details_never_contain_password_hash_or_session(self):
        self.client.login(username=self.admin.username, password=self.PASSWORD)
        self.client.post("/accounts/logout/")

        serialized_details = " ".join(
            str(event.details) for event in AuditLog.objects.all()
        )
        self.assertNotIn(self.PASSWORD, serialized_details)
        self.assertNotIn(self.admin.password, serialized_details)
        self.assertNotIn("sessionid", serialized_details.lower())

    def test_audit_020_consultant_audit_page_is_forbidden(self):
        self.client.force_login(self.consultant)

        response = self.client.get(self.audit_url)

        self.assertEqual(response.status_code, 403)

    def test_audit_021_agent_audit_page_is_forbidden(self):
        self.client.force_login(self.agent)

        response = self.client.get(self.audit_url)

        self.assertEqual(response.status_code, 403)

    def test_audit_022_administrator_audit_page_is_allowed(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.audit_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Journal d’audit")

    def test_audit_023_superuser_audit_page_is_allowed(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.audit_url)

        self.assertEqual(response.status_code, 200)

    def test_audit_024_anonymous_audit_page_redirects_to_login(self):
        response = self.client.get(self.audit_url)

        self.assertRedirects(response, "/accounts/login/?next=/audit/")

    def test_audit_025_audit_page_is_paginated(self):
        for index in range(26):
            AuditLog.objects.create(
                actor=self.admin,
                actor_identifier=self.admin.username,
                action=AuditAction.LOGIN,
                details={"source": "web"},
            )
        self.client.force_login(self.admin)

        response = self.client.get(self.audit_url)

        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["events"]), 25)

    def test_audit_026_audit_events_are_ordered_descending(self):
        older = AuditLog.objects.create(
            actor=self.admin,
            actor_identifier=self.admin.username,
            action=AuditAction.LOGIN,
        )
        newer = AuditLog.objects.create(
            actor=self.admin,
            actor_identifier=self.admin.username,
            action=AuditAction.LOGOUT,
        )
        AuditLog.objects.filter(pk=older.pk).update(
            timestamp=timezone.now() - timedelta(days=1)
        )
        AuditLog.objects.filter(pk=newer.pk).update(timestamp=timezone.now())
        self.client.force_login(self.admin)

        response = self.client.get(self.audit_url)

        events = list(response.context["events"])
        self.assertLess(events.index(newer), events.index(older))

    def test_audit_027_admin_is_read_only(self):
        model_admin = admin.site._registry[AuditLog]
        request = RequestFactory().get("/admin/audit/auditlog/")
        request.user = self.superuser

        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertIn("details", model_admin.get_readonly_fields(request))

    def test_audit_028_admin_disallows_deletion(self):
        model_admin = admin.site._registry[AuditLog]
        request = RequestFactory().get("/admin/audit/auditlog/")
        request.user = self.superuser

        self.assertFalse(model_admin.has_delete_permission(request))

    def test_audit_029_admin_disallows_manual_creation(self):
        model_admin = admin.site._registry[AuditLog]
        request = RequestFactory().get("/admin/audit/auditlog/")
        request.user = self.superuser

        self.assertFalse(model_admin.has_add_permission(request))

    def test_audit_030_archive_list_and_search_do_not_create_view_events(self):
        archive = self.create_archive()
        self.client.force_login(self.consultant)

        self.client.get("/archives/")
        self.client.get("/archives/", {"q": archive.title})

        self.assertFalse(self.audit_events(AuditAction.ARCHIVE_VIEW, archive).exists())
