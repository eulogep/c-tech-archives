"""Tests de comportement et de structure pour la refonte UI T-015."""

from hashlib import sha256
from pathlib import Path
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


class FinalInterfaceTests(TestCase):
    """Scénarios UI-001 à UI-020 sans tests pixel-perfect."""

    PASSWORD = "MotDePasse-UI-2026"
    PDF_CONTENT = b"%PDF-1.4\nfinal ui synthetic document\n"

    def setUp(self):
        self.private_media = TemporaryDirectory()
        self.settings_override = override_settings(PRIVATE_MEDIA_ROOT=self.private_media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.private_media.cleanup)

        user_model = get_user_model()
        self.admin_user = user_model.objects.create_user(
            username="ui-admin",
            email="ui-admin@example.test",
            password=self.PASSWORD,
            role=Role.ADMINISTRATEUR,
        )
        self.agent = user_model.objects.create_user(
            username="ui-agent",
            email="ui-agent@example.test",
            password=self.PASSWORD,
            role=Role.AGENT_ARCHIVES,
        )
        self.consultant = user_model.objects.create_user(
            username="ui-consultant",
            email="ui-consultant@example.test",
            password=self.PASSWORD,
            role=Role.CONSULTANT,
        )
        self.service = Service.objects.create(name="Service interface")
        self.category = Category.objects.create(name="Catégorie interface")
        self.document_type = DocumentType.objects.create(name="Type interface")
        self.public_archive = self.create_archive("CT-UI-PUBLIC", ConfidentialityLevel.PUBLIC)

    def create_archive(self, reference, confidentiality_level, **overrides):
        defaults = {
            "reference": reference,
            "title": "Archive interface synthétique",
            "description": "Donnée synthétique pour la revue UI.",
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

    def test_ui_001_login_renders_form_and_csrf(self):
        response = self.client.get("/accounts/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Accès sécurisé")
        self.assertContains(response, 'method="post"')
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, 'for="id_username"')
        self.assertContains(response, 'for="id_password"')

    def test_ui_002_authenticated_user_sees_primary_navigation(self):
        self.client.force_login(self.consultant)

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Navigation principale"')
        self.assertContains(response, "Tableau de bord")
        self.assertContains(response, "Archives")
        self.assertContains(response, self.consultant.username)

    def test_ui_003_consultant_does_not_see_create_archive_navigation(self):
        self.client.force_login(self.consultant)

        response = self.client.get("/")

        self.assertNotContains(response, "Nouvelle archive")

    def test_ui_004_agent_sees_create_archive_navigation(self):
        self.client.force_login(self.agent)

        response = self.client.get("/")

        self.assertContains(response, "Nouvelle archive")

    def test_ui_005_consultant_and_agent_do_not_see_audit_navigation(self):
        for user in (self.consultant, self.agent):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get("/")
                self.assertNotContains(response, "Journal d’audit")

    def test_ui_006_admin_sees_audit_navigation(self):
        self.client.force_login(self.admin_user)

        response = self.client.get("/")

        self.assertContains(response, "Journal d’audit")

    def test_ui_007_logout_remains_a_csrf_protected_post_form(self):
        self.client.force_login(self.agent)

        response = self.client.get("/")

        self.assertContains(
            response,
            '<form class="logout-form" method="post" action="/accounts/logout/">',
        )
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, 'type="submit">Déconnexion')

    def test_ui_008_dashboard_renders_the_six_authorized_metrics(self):
        self.client.force_login(self.consultant)

        response = self.client.get("/")

        for label in (
            "Archives visibles",
            "Archives actives",
            "Archives archivées",
            "Services actifs",
            "Catégories actives",
            "Types documentaires actifs",
        ):
            with self.subTest(label=label):
                self.assertContains(response, label)

    def test_ui_009_archive_list_renders_textual_status_and_confidentiality_badges(self):
        self.client.force_login(self.consultant)

        response = self.client.get("/archives/")

        self.assertContains(response, "badge-active")
        self.assertContains(response, "badge-public")
        self.assertContains(response, self.public_archive.get_status_display())
        self.assertContains(response, self.public_archive.get_confidentiality_level_display())

    def test_ui_010_search_remains_a_get_form(self):
        self.client.force_login(self.consultant)

        response = self.client.get("/archives/")

        self.assertContains(response, '<form class="filter-panel" method="get"')
        self.assertContains(response, "Recherche et filtres")

    def test_ui_011_pagination_preserves_active_query_string(self):
        for index in range(21):
            self.create_archive(f"CT-UI-PAGE-{index:02d}", ConfidentialityLevel.PUBLIC)
        self.client.force_login(self.consultant)

        response = self.client.get("/archives/?q=interface&page=1")

        self.assertContains(response, "Page 1 sur 2")
        self.assertContains(response, "?q=interface&amp;page=2")

    def test_ui_012_archive_detail_renders_available_document_actions(self):
        self.client.force_login(self.agent)

        response = self.client.get(f"/archives/{self.public_archive.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Télécharger le fichier")
        self.assertContains(response, "Vérifier l’intégrité")

    def test_ui_013_consultant_does_not_see_update_button(self):
        self.client.force_login(self.consultant)

        response = self.client.get(f"/archives/{self.public_archive.pk}/")

        self.assertNotContains(response, "Modifier")

    def test_ui_014_agent_sees_update_button_for_visible_archive(self):
        self.client.force_login(self.agent)

        response = self.client.get(f"/archives/{self.public_archive.pk}/")

        self.assertContains(response, "Modifier")

    def test_ui_015_integrity_action_remains_a_csrf_protected_post_form(self):
        self.client.force_login(self.agent)

        response = self.client.get(f"/archives/{self.public_archive.pk}/")

        self.assertContains(
            response,
            f'action="/archives/{self.public_archive.pk}/verify-integrity/"',
        )
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, 'method="post"')

    def test_ui_016_audit_screen_remains_limited_to_administrators(self):
        self.client.force_login(self.consultant)
        denied_response = self.client.get("/audit/")
        self.assertEqual(denied_response.status_code, 403)

        self.client.force_login(self.admin_user)
        allowed_response = self.client.get("/audit/")
        self.assertEqual(allowed_response.status_code, 200)
        self.assertContains(allowed_response, "Journal d’audit")

    def test_ui_017_archive_empty_state_is_present(self):
        Archive.objects.all().delete()
        self.client.force_login(self.admin_user)

        response = self.client.get("/archives/")

        self.assertContains(response, "Aucune archive disponible")

    def test_ui_018_no_result_state_is_present(self):
        self.client.force_login(self.consultant)

        response = self.client.get("/archives/?q=introuvable-ui")

        self.assertContains(response, "Aucune archive ne correspond aux critères.")

    def test_ui_019_templates_do_not_use_public_file_urls(self):
        templates_root = Path(__file__).resolve().parents[1] / "templates"
        rendered_sources = "\n".join(
            template.read_text(encoding="utf-8")
            for template in templates_root.rglob("*.html")
        )

        self.assertNotIn("archive.file.url", rendered_sources)

    def test_ui_020_archive_detail_does_not_display_checksum(self):
        self.client.force_login(self.agent)

        response = self.client.get(f"/archives/{self.public_archive.pk}/")

        self.assertNotContains(response, self.public_archive.checksum)

    def test_ui_021_accessibility_landmarks_titles_and_visible_focus_are_present(self):
        self.client.force_login(self.agent)

        response = self.client.get("/archives/")
        project_root = Path(__file__).resolve().parents[1]
        base_template = (project_root / "templates" / "base.html").read_text(
            encoding="utf-8"
        )
        stylesheet = (project_root / "static" / "css" / "app.css").read_text(
            encoding="utf-8"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>Archives | C-Tech Archives</title>")
        self.assertIn('aria-label="Navigation principale"', base_template)
        self.assertIn('id="main-content"', base_template)
        self.assertIn(":focus-visible", stylesheet)
