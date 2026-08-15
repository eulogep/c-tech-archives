"""Tests du tableau de bord de synthèse des archives."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Role
from archives.models import (
    Archive,
    ArchiveStatus,
    Category,
    ConfidentialityLevel,
    DocumentType,
    Service,
)


class DashboardTests(TestCase):
    """Couvre les indicateurs agrégés et l’aperçu documentaire filtré."""

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="dashboard-user",
            email="dashboard-user@example.test",
            password="MotDePasse-Dashboard-2026",
            role=Role.ADMINISTRATEUR,
        )
        self.dashboard_url = "/"

    def create_archive(
        self,
        index,
        status=ArchiveStatus.ACTIVE,
        checksum="",
        reference=None,
        title=None,
        confidentiality_level=ConfidentialityLevel.INTERNAL,
    ):
        service, _ = Service.objects.get_or_create(name="Direction des opérations")
        category, _ = Category.objects.get_or_create(name="Rapport")
        document_type, _ = DocumentType.objects.get_or_create(name="Rapport opérationnel")
        archive = Archive.objects.create(
            reference=reference or f"CT-2026-{index:06d}",
            title=title or f"Archive de démonstration {index}",
            category=category,
            document_type=document_type,
            service=service,
            uploaded_by=self.user,
            document_date=date(2026, 1, min(index, 28)),
            status=status,
            checksum=checksum,
            confidentiality_level=confidentiality_level,
        )
        return archive

    def test_dash_001_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.dashboard_url)

        self.assertRedirects(response, "/accounts/login/?next=/")

    def test_dash_002_authenticated_user_can_access_dashboard(self):
        self.client.force_login(self.user)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tableau de bord")

    def test_dash_003_empty_database_displays_zero_aggregates_and_empty_state(self):
        self.client.force_login(self.user)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.context["archive_count"], 0)
        self.assertEqual(response.context["active_service_count"], 0)
        self.assertContains(response, "Dernières archives visibles")
        self.assertContains(response, "Aucune archive visible")

    def test_dash_004_total_archive_counter_reflects_database(self):
        for index in range(1, 4):
            self.create_archive(index)
        self.client.force_login(self.user)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.context["archive_count"], 3)

    def test_dash_005_status_counters_distinguish_active_and_archived(self):
        for index in range(1, 4):
            self.create_archive(index, status=ArchiveStatus.ACTIVE)
        for index in range(4, 6):
            self.create_archive(index, status=ArchiveStatus.ARCHIVED)
        self.client.force_login(self.user)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.context["active_archive_count"], 3)
        self.assertEqual(response.context["archived_archive_count"], 2)

    def test_dash_006_only_active_references_are_counted(self):
        Service.objects.create(name="Service actif", is_active=True)
        Service.objects.create(name="Service inactif", is_active=False)
        Category.objects.create(name="Catégorie active", is_active=True)
        Category.objects.create(name="Catégorie inactive", is_active=False)
        DocumentType.objects.create(name="Type actif", is_active=True)
        DocumentType.objects.create(name="Type inactif", is_active=False)
        self.create_archive(1)
        self.client.force_login(self.user)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.context["active_service_count"], 1)
        self.assertEqual(response.context["active_category_count"], 1)
        self.assertEqual(response.context["active_document_type_count"], 1)

    def test_dash_007_hidden_confidential_archive_metadata_is_not_exposed(self):
        reference = "CT-2026-999999"
        title = "Document extrêmement confidentiel"
        self.create_archive(
            1,
            reference=reference,
            title=title,
            confidentiality_level=ConfidentialityLevel.CONFIDENTIAL,
        )
        self.user.role = Role.CONSULTANT
        self.user.save(update_fields=["role"])
        self.client.force_login(self.user)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.context["archive_count"], 0)
        self.assertNotContains(response, reference)
        self.assertNotContains(response, title)

    def test_dash_008_aggregate_counters_remain_correct_with_multiple_archives(self):
        for index in range(1, 4):
            self.create_archive(index, status=ArchiveStatus.ACTIVE)
        for index in range(4, 6):
            self.create_archive(index, status=ArchiveStatus.ARCHIVED)
        self.client.force_login(self.user)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.context["archive_count"], 5)
        self.assertEqual(response.context["active_archive_count"], 3)
        self.assertEqual(response.context["archived_archive_count"], 2)

    def test_dash_009_technical_sensitive_values_are_not_exposed_in_html(self):
        checksum = "a" * 64
        confidential_title = "Titre confidentiel créé pour le test"
        self.create_archive(
            1,
            checksum=checksum,
            title=confidential_title,
            confidentiality_level=ConfidentialityLevel.CONFIDENTIAL,
        )
        self.client.force_login(self.user)

        response = self.client.get(self.dashboard_url)

        self.assertNotContains(response, checksum)
        self.assertNotContains(response, self.user.password)
        self.assertContains(response, confidential_title)

    def test_dash_010_dashboard_context_exposes_filtered_recent_archives(self):
        self.create_archive(1)
        self.client.force_login(self.user)

        response = self.client.get(self.dashboard_url)

        self.assertNotIn("latest_archives", response.context)
        self.assertIn("recent_archives", response.context)
        self.assertContains(response, "Dernières archives visibles")
