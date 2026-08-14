"""Revue de sécurité transverse T-014 du MVP C-Tech Archives."""

import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import Resolver404, resolve

from accounts.models import Role
from archives.integrity import IntegrityStatus, verify_archive_integrity
from archives.models import (
    Archive,
    ArchiveStatus,
    Category,
    ConfidentialityLevel,
    DocumentType,
    Service,
)
from archives.permissions import has_archive_access, visible_confidentiality_levels_for
from audit.models import AuditLog


class SecurityHardeningTests(TestCase):
    """Scénarios HARD-001 à HARD-025, complémentaires aux tests de tickets."""

    PDF_CONTENT = b"%PDF-1.4\nsecurity hardening synthetic document\n"
    PASSWORD = "MotDePasse-Security-2026"

    def setUp(self):
        self.private_media = TemporaryDirectory()
        self.settings_override = override_settings(PRIVATE_MEDIA_ROOT=self.private_media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.private_media.cleanup)

        user_model = get_user_model()
        self.admin_user = user_model.objects.create_user(
            username="hard-admin",
            email="hard-admin@example.test",
            password=self.PASSWORD,
            role=Role.ADMINISTRATEUR,
        )
        self.agent = user_model.objects.create_user(
            username="hard-agent",
            email="hard-agent@example.test",
            password="MotDePasse-Agent-2026",
            role=Role.AGENT_ARCHIVES,
        )
        self.consultant = user_model.objects.create_user(
            username="hard-consultant",
            email="hard-consultant@example.test",
            password="MotDePasse-Consultant-2026",
            role=Role.CONSULTANT,
        )
        self.inactive = user_model.objects.create_user(
            username="hard-inactive",
            email="hard-inactive@example.test",
            password="MotDePasse-Inactif-2026",
            is_active=False,
            role=Role.CONSULTANT,
        )
        self.superuser = user_model.objects.create_superuser(
            username="hard-superuser",
            email="hard-superuser@example.test",
            password="MotDePasse-Superuser-2026",
        )
        self.service = Service.objects.create(name="Service durcissement")
        self.category = Category.objects.create(name="Catégorie durcissement")
        self.document_type = DocumentType.objects.create(name="Type durcissement")

        self.public_archive = self.create_archive("CT-HARD-PUBLIC", ConfidentialityLevel.PUBLIC)
        self.internal_archive = self.create_archive("CT-HARD-INTERNAL", ConfidentialityLevel.INTERNAL)
        self.confidential_archive = self.create_archive(
            "CT-HARD-CONFIDENTIAL", ConfidentialityLevel.CONFIDENTIAL
        )

    def create_archive(self, reference, level, **overrides):
        defaults = {
            "reference": reference,
            "title": "Archive synthétique de durcissement",
            "description": "Donnée synthétique de test de sécurité",
            "category": self.category,
            "document_type": self.document_type,
            "service": self.service,
            "uploaded_by": self.admin_user,
            "status": ArchiveStatus.ACTIVE,
            "confidentiality_level": level,
            "file": SimpleUploadedFile(
                f"{reference}.pdf", self.PDF_CONTENT, content_type="application/pdf"
            ),
            "file_size": len(self.PDF_CONTENT),
            "checksum": sha256(self.PDF_CONTENT).hexdigest(),
        }
        defaults.update(overrides)
        return Archive.objects.create(**defaults)

    def archive_payload(self, reference, **overrides):
        data = {
            "reference": reference,
            "title": "Archive créée durant le durcissement",
            "description": "Contenu synthétique",
            "category": str(self.category.pk),
            "document_type": str(self.document_type.pk),
            "service": str(self.service.pk),
            "document_date": "2026-08-14",
            "status": ArchiveStatus.ACTIVE,
            "confidentiality_level": ConfidentialityLevel.PUBLIC,
        }
        data.update(overrides)
        return data

    @staticmethod
    def detail_url(archive):
        return f"/archives/{archive.pk}/"

    @staticmethod
    def edit_url(archive):
        return f"/archives/{archive.pk}/edit/"

    @staticmethod
    def download_url(archive):
        return f"/archives/{archive.pk}/download/"

    @staticmethod
    def verify_url(archive):
        return f"/archives/{archive.pk}/verify-integrity/"

    def test_hard_001_idor_detail_hidden_archive_is_404(self):
        self.client.force_login(self.consultant)

        response = self.client.get(self.detail_url(self.internal_archive))

        self.assertEqual(response.status_code, 404)

    def test_hard_002_idor_edit_hidden_archive_is_404(self):
        self.client.force_login(self.agent)

        response = self.client.get(self.edit_url(self.confidential_archive))

        self.assertEqual(response.status_code, 404)

    def test_hard_003_idor_download_hidden_archive_is_404(self):
        self.client.force_login(self.consultant)

        response = self.client.get(self.download_url(self.internal_archive))

        self.assertEqual(response.status_code, 404)

    def test_hard_004_idor_integrity_hidden_archive_is_404(self):
        self.client.force_login(self.agent)

        response = self.client.post(self.verify_url(self.confidential_archive))

        self.assertEqual(response.status_code, 404)

    def test_hard_005_mass_assignment_server_fields_are_ignored(self):
        self.client.force_login(self.agent)
        forged_checksum = "0" * 64

        response = self.client.post(
            "/archives/new/",
            self.archive_payload(
                "CT-HARD-MASS-005",
                file=SimpleUploadedFile(
                    "mass.pdf", self.PDF_CONTENT, content_type="application/pdf"
                ),
                uploaded_by=str(self.admin_user.pk),
                file_size="9999999",
                checksum=forged_checksum,
                created_at="2000-01-01T00:00:00Z",
                updated_at="2000-01-01T00:00:00Z",
                is_staff="1",
                is_superuser="1",
                role=Role.ADMINISTRATEUR,
            ),
        )

        archive = Archive.objects.get(reference="CT-HARD-MASS-005")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(archive.uploaded_by, self.agent)
        self.assertEqual(archive.file_size, len(self.PDF_CONTENT))
        self.assertEqual(archive.checksum, sha256(self.PDF_CONTENT).hexdigest())
        self.assertNotEqual(archive.checksum, forged_checksum)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.role, Role.AGENT_ARCHIVES)
        self.assertFalse(self.agent.is_staff)
        self.assertFalse(self.agent.is_superuser)

    def test_hard_006_xss_metadata_is_escaped(self):
        archive = self.create_archive(
            "CT-HARD-XSS-006",
            ConfidentialityLevel.PUBLIC,
            title='<script>alert("xss")</script>',
            description='<script>alert("xss")</script>',
        )
        self.client.force_login(self.consultant)

        response = self.client.get(self.detail_url(archive))

        self.assertContains(response, "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;", html=False)
        self.assertNotContains(response, '<script>alert("xss")</script>', html=False)

    def test_hard_007_xss_search_is_escaped(self):
        self.client.force_login(self.consultant)

        response = self.client.get("/archives/", {"q": '<script>alert("xss")</script>'})

        self.assertContains(response, "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;", html=False)
        self.assertNotContains(response, '<script>alert("xss")</script>', html=False)

    def test_hard_008_injection_like_search_is_treated_as_data(self):
        self.client.force_login(self.consultant)

        response = self.client.get("/archives/", {"q": "' OR 1=1 --"})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.public_archive.reference)

    def test_hard_009_unix_path_traversal_stays_inside_private_root(self):
        self.client.force_login(self.admin_user)

        self.client.post(
            "/archives/new/",
            self.archive_payload(
                "CT-HARD-PATH-009",
                file=SimpleUploadedFile(
                    "../../secret.pdf", self.PDF_CONTENT, content_type="application/pdf"
                ),
            ),
        )
        archive = Archive.objects.get(reference="CT-HARD-PATH-009")

        self.assertTrue(
            Path(archive.file.path).resolve().is_relative_to(Path(self.private_media.name).resolve())
        )

    def test_hard_010_windows_path_traversal_stays_inside_private_root(self):
        self.client.force_login(self.admin_user)

        self.client.post(
            "/archives/new/",
            self.archive_payload(
                "CT-HARD-PATH-010",
                file=SimpleUploadedFile(
                    r"..\..\secret.pdf", self.PDF_CONTENT, content_type="application/pdf"
                ),
            ),
        )
        archive = Archive.objects.get(reference="CT-HARD-PATH-010")

        self.assertTrue(
            Path(archive.file.path).resolve().is_relative_to(Path(self.private_media.name).resolve())
        )

    def test_hard_011_private_storage_has_no_public_media_route(self):
        self.assertIsNone(self.public_archive.file.storage.base_url)
        with self.assertRaises(Resolver404):
            resolve(f"/media/{self.public_archive.file.name}")

    def test_hard_012_audit_details_never_expose_sensitive_values(self):
        self.client.login(username=self.admin_user.username, password=self.PASSWORD)
        self.client.post("/accounts/logout/")
        self.client.force_login(self.consultant)
        self.client.post(self.verify_url(self.public_archive))

        serialized = " ".join(
            f"{event.details} {event.archive_reference}" for event in AuditLog.objects.all()
        )
        for forbidden in (
            self.PASSWORD,
            self.admin_user.password,
            "sessionid",
            "authorization",
            self.public_archive.checksum,
            self.public_archive.file.name,
        ):
            self.assertNotIn(forbidden.lower(), serialized.lower())

    def test_hard_013_audit_admin_cannot_be_edited(self):
        model_admin = admin.site._registry[AuditLog]
        request = SimpleNamespace(user=self.superuser)

        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_add_permission(request))

    def test_hard_014_audit_admin_cannot_be_deleted(self):
        model_admin = admin.site._registry[AuditLog]
        request = SimpleNamespace(user=self.superuser)

        self.assertFalse(model_admin.has_delete_permission(request))

    def test_hard_015_malformed_archive_id_returns_404(self):
        self.client.force_login(self.admin_user)

        response = self.client.get("/archives/not-an-integer/")

        self.assertEqual(response.status_code, 404)

    def test_hard_016_missing_private_file_returns_controlled_404(self):
        self.public_archive.file.storage.delete(self.public_archive.file.name)
        self.client.force_login(self.consultant)

        response = self.client.get(self.download_url(self.public_archive))

        self.assertEqual(response.status_code, 404)

    def test_hard_017_integrity_mismatch_keeps_checksum_reference(self):
        original_checksum = self.public_archive.checksum
        with self.public_archive.file.storage.open(self.public_archive.file.name, "wb") as file_obj:
            file_obj.write(b"%PDF-1.4\nmodified synthetic security document\n")

        result = verify_archive_integrity(self.public_archive)
        self.public_archive.refresh_from_db()

        self.assertEqual(result.status, IntegrityStatus.MISMATCH)
        self.assertEqual(self.public_archive.checksum, original_checksum)

    def test_hard_018_unknown_role_is_denied_by_default(self):
        invalid_user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            role="UNKNOWN_ROLE",
        )

        self.assertFalse(has_archive_access(invalid_user))
        self.assertEqual(visible_confidentiality_levels_for(invalid_user), frozenset())

    def test_hard_019_inactive_user_cannot_authenticate(self):
        self.assertFalse(
            self.client.login(
                username=self.inactive.username, password="MotDePasse-Inactif-2026"
            )
        )

    def test_hard_020_external_next_is_neutralized(self):
        response = self.client.post(
            "/accounts/login/?next=https://attacker.example/",
            {"username": self.admin_user.username, "password": self.PASSWORD},
        )

        self.assertRedirects(response, "/")

    def test_hard_021_create_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.agent)

        response = csrf_client.post(
            "/archives/new/", self.archive_payload("CT-HARD-CSRF-021")
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Archive.objects.filter(reference="CT-HARD-CSRF-021").exists())

    def test_hard_022_update_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.agent)

        response = csrf_client.post(
            self.edit_url(self.public_archive),
            self.archive_payload(self.public_archive.reference, title="Tentative CSRF"),
        )

        self.assertEqual(response.status_code, 403)
        self.public_archive.refresh_from_db()
        self.assertEqual(self.public_archive.title, "Archive synthétique de durcissement")

    def test_hard_023_integrity_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.consultant)

        response = csrf_client.post(self.verify_url(self.public_archive))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(AuditLog.objects.filter(archive=self.public_archive).exists())

    def test_hard_024_logout_requires_post_and_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin_user)

        get_response = csrf_client.get("/accounts/logout/")
        post_response = csrf_client.post("/accounts/logout/")

        self.assertEqual(get_response.status_code, 405)
        self.assertEqual(post_response.status_code, 403)

    def test_hard_025_configuration_uses_environment_without_secret_fixture(self):
        project_root = Path(__file__).resolve().parents[1]
        settings_source = (project_root / "config" / "settings.py").read_text()
        env_example = (project_root / ".env.example").read_text()
        readme = (project_root / "README.md").read_text()

        self.assertIn("required_env(\"DJANGO_SECRET_KEY\")", settings_source)
        self.assertNotIn("django-insecure-", settings_source)
        self.assertNotIn(self.PASSWORD, env_example)
        self.assertNotIn(self.PASSWORD, readme)
        self.assertNotIn("DJANGO_ALLOWED_HOSTS=*", env_example)

    def test_hard_026_production_rejects_wildcard_allowed_hosts(self):
        """La configuration de production exige des hôtes explicites."""
        project_root = Path(__file__).resolve().parents[1]
        base_environment = {
            **os.environ,
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "DJANGO_ENV": "production",
            "DJANGO_DEBUG": "false",
        }

        for allowed_hosts in (
            "c-tech.example",
            "c-tech.example,www.c-tech.example",
        ):
            result = subprocess.run(
                [sys.executable, "-c", "import django; django.setup()"],
                cwd=str(project_root),
                env={**base_environment, "DJANGO_ALLOWED_HOSTS": allowed_hosts},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        wildcard_result = subprocess.run(
            [sys.executable, "-c", "import django; django.setup()"],
            cwd=str(project_root),
            env={**base_environment, "DJANGO_ALLOWED_HOSTS": "*"},
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(wildcard_result.returncode, 0)
        self.assertIn("ImproperlyConfigured", wildcard_result.stderr)
        self.assertIn("DJANGO_ALLOWED_HOSTS ne doit pas contenir '*'", wildcard_result.stderr)
