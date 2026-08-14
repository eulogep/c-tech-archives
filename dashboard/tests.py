"""Tests du tableau de bord de synthèse des archives."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from archives.models import Archive, ArchiveStatus, Category, DocumentType, Service


class DashboardTests(TestCase):
    """Couvre les indicateurs et la liste courte du tableau de bord T-007."""

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="dashboard-user",
            email="dashboard-user@example.test",
            password="MotDePasse-Dashboard-2026",
        )
        self.dashboard_url = "/"

    def create_archive(self, index, status=ArchiveStatus.ACTIVE, created_at=None, checksum=""):
        service, _ = Service.objects.get_or_create(name="Direction des opérations")
        category, _ = Category.objects.get_or_create(name="Rapport")
        document_type, _ = DocumentType.objects.get_or_create(name="Rapport opérationnel")
        archive = Archive.objects.create(
            reference=f"CT-2026-{index:06d}",
            title=f"Archive de démonstration {index}",
            category=category,
            document_type=document_type,
            service=service,
            uploaded_by=self.user,
            document_date=date(2026, 1, min(index, 28)),
            status=status,
            checksum=checksum,
        )
        if created_at is not None:
            Archive.objects.filter(pk=archive.pk).update(created_at=created_at)
            archive.refresh_from_db()
        return archive

    def test_dash_001_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.dashboard_url)

        self.assertRedirects(response, "/accounts/login/?next=/")

    def test_dash_002_authenticated_user_can_access_dashboard(self):
        self.client.force_login(self.user)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tableau de bord")

    def test_dash_003_empty_database_displays_zero_and_empty_state(self):
        self.client.force_login(self.user)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.context["archive_count"], 0)
        self.assertEqual(response.context["active_service_count"], 0)
        self.assertContains(response, "Aucune archive enregistrée.")

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
        self.client.force_login(self.user)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.context["active_service_count"], 1)
        self.assertEqual(response.context["active_category_count"], 1)
        self.assertEqual(response.context["active_document_type_count"], 1)

    def test_dash_007_latest_archives_are_limited_to_five(self):
        now = timezone.now()
        for index in range(1, 7):
            self.create_archive(index, created_at=now + timedelta(minutes=index))
        self.client.force_login(self.user)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(len(response.context["latest_archives"]), 5)

    def test_dash_008_latest_archives_are_ordered_by_creation_date_descending(self):
        now = timezone.now()
        oldest = self.create_archive(1, created_at=now)
        middle = self.create_archive(2, created_at=now + timedelta(minutes=1))
        newest = self.create_archive(3, created_at=now + timedelta(minutes=2))
        self.client.force_login(self.user)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(
            list(response.context["latest_archives"]),
            [newest, middle, oldest],
        )

    def test_dash_009_related_data_is_rendered_without_n_plus_one_queries(self):
        self.create_archive(1)
        self.client.force_login(self.user)

        with self.assertNumQueries(9):
            response = self.client.get(self.dashboard_url)

        self.assertContains(response, "Direction des opérations")
        self.assertContains(response, "Rapport")

    def test_dash_010_sensitive_values_are_not_exposed_in_html(self):
        checksum = "a" * 64
        self.create_archive(1, checksum=checksum)
        self.client.force_login(self.user)

        response = self.client.get(self.dashboard_url)

        self.assertNotContains(response, checksum)
        self.assertNotContains(response, self.user.password)
