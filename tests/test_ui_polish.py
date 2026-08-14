"""Tests de non-régression et de structure pour la finition UI/UX (T-016 / Final MVP)."""

from hashlib import sha256
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from accounts.models import Role
from archives.models import (
    Archive,
    ArchiveStatus,
    Category,
    ConfidentialityLevel,
    DocumentType,
    Service,
)
from audit.models import AuditAction, AuditLog


class UIPolishTests(TestCase):
    """Scénarios UI-POLISH-001 à UI-POLISH-010."""

    PASSWORD = "MotDePasse-UI-Polish-2026"
    PDF_CONTENT = b"%PDF-1.4\nsynthetic document for ui polish tests\n"

    def setUp(self):
        self.private_media = TemporaryDirectory()
        self.settings_override = override_settings(
            PRIVATE_MEDIA_ROOT=self.private_media.name
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.private_media.cleanup)

        user_model = get_user_model()
        self.admin_user = user_model.objects.create_user(
            username="polish-admin",
            email="polish-admin@example.test",
            password=self.PASSWORD,
            role=Role.ADMINISTRATEUR,
            is_staff=False,
            is_superuser=False,
        )
        self.tech_admin = user_model.objects.create_user(
            username="polish-euloge",
            email="polish-euloge@example.test",
            password=self.PASSWORD,
            role=Role.ADMINISTRATEUR,
            is_staff=True,
            is_superuser=True,
        )
        self.agent = user_model.objects.create_user(
            username="polish-agent",
            email="polish-agent@example.test",
            password=self.PASSWORD,
            role=Role.AGENT_ARCHIVES,
        )
        self.consultant = user_model.objects.create_user(
            username="polish-consultant",
            email="polish-consultant@example.test",
            password=self.PASSWORD,
            role=Role.CONSULTANT,
        )

        self.service = Service.objects.create(name="Service Polish")
        self.category = Category.objects.create(name="Catégorie Polish")
        self.document_type = DocumentType.objects.create(name="Type Polish")

        self.public_archive = self.create_archive(
            "CT-POLISH-PUB", ConfidentialityLevel.PUBLIC
        )
        self.internal_archive = self.create_archive(
            "CT-POLISH-INT", ConfidentialityLevel.INTERNAL
        )
        self.confidential_archive = self.create_archive(
            "CT-POLISH-CONF", ConfidentialityLevel.CONFIDENTIAL
        )

        AuditLog.objects.create(
            actor=self.admin_user,
            actor_identifier=self.admin_user.username,
            action=AuditAction.LOGIN,
            ip_address="127.0.0.1",
        )

    def create_archive(self, reference, confidentiality_level, **overrides):
        defaults = {
            "reference": reference,
            "title": f"Titre {reference}",
            "description": "Description synthétique de validation UI.",
            "category": self.category,
            "document_type": self.document_type,
            "service": self.service,
            "uploaded_by": self.admin_user,
            "status": ArchiveStatus.ACTIVE,
            "confidentiality_level": confidentiality_level,
            "file": SimpleUploadedFile(
                f"{reference}.pdf", self.PDF_CONTENT, content_type="application/pdf"
            ),
            "file_size": len(self.PDF_CONTENT),
            "checksum": sha256(self.PDF_CONTENT).hexdigest(),
        }
        defaults.update(overrides)
        return Archive.objects.create(**defaults)

    def test_ui_polish_001_consultant_archive_summary_does_not_leak_hidden_counts(self):
        """UI-POLISH-001 : La synthèse consultant ne fait mention d'aucune archive interne/confidentielle."""
        self.client.force_login(self.consultant)
        response = self.client.get("/archives/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public :")
        self.assertNotContains(response, "Interne :")
        self.assertNotContains(response, "Confidentiel :")

    def test_ui_polish_002_agent_archive_summary_does_not_leak_confidential_counts(self):
        """UI-POLISH-002 : La synthèse agent mentionne public et interne mais jamais confidentiel."""
        self.client.force_login(self.agent)
        response = self.client.get("/archives/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public :")
        self.assertContains(response, "Interne :")
        self.assertNotContains(response, "Confidentiel :")

    def test_ui_polish_003_administrator_archive_summary_includes_all_visible_levels(self):
        """UI-POLISH-003 : La synthèse administrateur affiche tous les niveaux."""
        self.client.force_login(self.admin_user)
        response = self.client.get("/archives/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public :")
        self.assertContains(response, "Interne :")
        self.assertContains(response, "Confidentiel :")

    def test_ui_polish_004_integrity_action_remains_post_and_csrf(self):
        """UI-POLISH-004 : L'action d'intégrité reste un formulaire POST protégé par CSRF."""
        self.client.force_login(self.admin_user)
        response = self.client.get(f"/archives/{self.public_archive.pk}/")

        self.assertContains(
            response, f'action="/archives/{self.public_archive.pk}/verify-integrity/"'
        )
        self.assertContains(response, 'method="post"')
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_ui_polish_005_topbar_distinguishes_role_and_superuser_privileges(self):
        """UI-POLISH-005 : Distinction nette entre rôle métier et superutilisateur technique."""
        self.client.force_login(self.admin_user)
        resp_steven = self.client.get("/")
        self.assertContains(resp_steven, "Administrateur")
        self.assertNotContains(resp_steven, "Superutilisateur technique")

        self.client.force_login(self.tech_admin)
        resp_euloge = self.client.get("/")
        self.assertContains(resp_euloge, "Administrateur")
        self.assertContains(resp_euloge, "Superutilisateur technique")

    def test_ui_polish_006_audit_filtering_works_without_regression(self):
        """UI-POLISH-006 : Les filtres d'audit fonctionnent pour les administrateurs."""
        self.client.force_login(self.admin_user)
        response = self.client.get("/audit/?action=LOGIN")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Connexion")

    def test_ui_polish_007_detail_page_sections_are_present(self):
        """UI-POLISH-007 : La page détail contient les sections structurées A, B, C, D."""
        self.client.force_login(self.admin_user)
        response = self.client.get(f"/archives/{self.public_archive.pk}/")

        self.assertContains(response, "A. Identification")
        self.assertContains(response, "B. Classification")
        self.assertContains(response, "C. Document")
        self.assertContains(response, "D. Intégrité")

    def test_ui_polish_008_form_helpers_are_rendered(self):
        """UI-POLISH-008 : Le formulaire d'archive affiche les textes d'aide clairs."""
        self.client.force_login(self.admin_user)
        response = self.client.get("/archives/new/")

        self.assertContains(response, "Identifiant documentaire unique.")
        self.assertContains(response, "Détermine quels rôles peuvent consulter cette archive.")

    def test_ui_polish_009_unauthorized_actions_are_not_rendered(self):
        """UI-POLISH-009 : Les actions non autorisées (création pour consultant) ne sont pas affichées."""
        self.client.force_login(self.consultant)
        response = self.client.get("/")
        self.assertNotContains(response, "/archives/new/")

    def test_ui_polish_010_direct_url_protections_remain_authoritative(self):
        """UI-POLISH-010 : Les accès directs non autorisés renvoient 403 / 404."""
        self.client.force_login(self.consultant)
        self.assertEqual(self.client.get("/archives/new/").status_code, 403)
        self.assertEqual(
            self.client.get(f"/archives/{self.confidential_archive.pk}/").status_code,
            404,
        )

    def test_ui_polish_011_consultant_recent_archives_contain_public_only(self):
        self.client.force_login(self.consultant)

        response = self.client.get("/")

        self.assertContains(response, "Dernières archives visibles")
        self.assertContains(response, self.public_archive.reference)
        self.assertNotContains(response, self.internal_archive.reference)
        self.assertNotContains(response, self.confidential_archive.reference)

    def test_ui_polish_012_agent_recent_archives_exclude_confidential(self):
        self.client.force_login(self.agent)

        response = self.client.get("/")

        self.assertContains(response, self.public_archive.reference)
        self.assertContains(response, self.internal_archive.reference)
        self.assertNotContains(response, self.confidential_archive.reference)

    def test_ui_polish_013_administrator_recent_archives_include_confidential(self):
        self.client.force_login(self.admin_user)

        response = self.client.get("/")

        self.assertContains(response, self.confidential_archive.reference)

    def test_ui_polish_014_recent_archives_are_limited_to_five(self):
        for index in range(5):
            self.create_archive(
                f"CT-POLISH-RECENT-{index}", ConfidentialityLevel.PUBLIC
            )
        self.client.force_login(self.consultant)

        response = self.client.get("/")

        self.assertEqual(len(response.context["recent_archives"]), 5)
        self.assertNotContains(response, self.public_archive.reference)

    def test_ui_polish_015_recent_audit_activity_is_hidden_from_unauthorized_roles(self):
        for user in (self.consultant, self.agent):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get("/")
                self.assertNotContains(response, "Activité récente")
                self.assertNotIn("recent_audit_events", response.context)

    def test_ui_polish_016_recent_audit_activity_is_visible_to_business_admin(self):
        self.client.force_login(self.admin_user)

        response = self.client.get("/")

        self.assertContains(response, "Activité récente")
        self.assertContains(response, "Connexion réussie")
        self.assertIn("recent_audit_events", response.context)

    def test_ui_polish_017_list_integrity_action_remains_post_and_csrf(self):
        self.client.force_login(self.consultant)

        response = self.client.get("/archives/")

        self.assertContains(
            response,
            f'action="/archives/{self.public_archive.pk}/verify-integrity/"',
        )
        self.assertContains(response, 'method="post"')
        self.assertContains(response, "csrfmiddlewaretoken")
