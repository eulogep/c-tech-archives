"""Tests des modèles métier fondamentaux des archives."""

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import Resolver404, resolve

from accounts.models import Role
from .models import (
    Archive,
    ArchiveStatus,
    Category,
    ConfidentialityLevel,
    DocumentType,
    Service,
)


class ArchiveDomainModelTests(TestCase):
    """Vérifie les règles de persistance et de conservation de T-004."""

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="archive-owner",
            email="archive-owner@example.test",
            password="MotDePasse-Test-2026",
        )
        self.service = Service.objects.create(name="Direction administrative")
        self.category = Category.objects.create(name="Contrat")
        self.document_type = DocumentType.objects.create(name="Contrat de prestation")

    def create_archive(self, **overrides):
        defaults = {
            "reference": f"CT-2026-{Archive.objects.count() + 1:06d}",
            "title": "Contrat de démonstration",
            "category": self.category,
            "document_type": self.document_type,
            "service": self.service,
            "uploaded_by": self.user,
            "document_date": date(2026, 1, 15),
            "status": ArchiveStatus.ACTIVE,
            "confidentiality_level": ConfidentialityLevel.INTERNAL,
            "file_size": 0,
        }
        defaults.update(overrides)
        return Archive.objects.create(**defaults)

    def test_service_can_be_created_with_timestamps(self):
        self.assertEqual(self.service.name, "Direction administrative")
        self.assertTrue(self.service.is_active)
        self.assertIsNotNone(self.service.created_at)
        self.assertIsNotNone(self.service.updated_at)
        self.assertEqual(str(self.service), "Direction administrative")

    def test_service_name_is_unique(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Service.objects.create(name="Direction administrative")

    def test_category_can_be_created(self):
        self.assertEqual(self.category.name, "Contrat")
        self.assertTrue(self.category.is_active)
        self.assertEqual(str(self.category), "Contrat")

    def test_document_type_can_be_created(self):
        self.assertEqual(self.document_type.name, "Contrat de prestation")
        self.assertTrue(self.document_type.is_active)
        self.assertEqual(str(self.document_type), "Contrat de prestation")

    def test_archive_can_be_created_with_domain_relations(self):
        archive = self.create_archive()

        self.assertEqual(archive.category, self.category)
        self.assertEqual(archive.document_type, self.document_type)
        self.assertEqual(archive.service, self.service)
        self.assertEqual(archive.uploaded_by, self.user)
        self.assertEqual(archive.status, ArchiveStatus.ACTIVE)
        self.assertEqual(archive.confidentiality_level, ConfidentialityLevel.INTERNAL)

    def test_archive_reference_is_unique(self):
        archive = self.create_archive(reference="CT-2026-000100")

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_archive(reference=archive.reference)

    def test_uploaded_by_references_the_custom_user(self):
        archive = self.create_archive()

        self.assertEqual(Archive._meta.get_field("uploaded_by").remote_field.model, get_user_model())
        self.assertEqual(self.user.uploaded_archives.get(), archive)

    def test_service_deletion_is_protected_when_referenced_by_archive(self):
        self.create_archive()

        with self.assertRaises(ProtectedError):
            self.service.delete()

        self.assertTrue(Service.objects.filter(pk=self.service.pk).exists())

    def test_category_deletion_is_protected_when_referenced_by_archive(self):
        self.create_archive()

        with self.assertRaises(ProtectedError):
            self.category.delete()

        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_document_type_deletion_is_protected_when_referenced_by_archive(self):
        self.create_archive()

        with self.assertRaises(ProtectedError):
            self.document_type.delete()

        self.assertTrue(DocumentType.objects.filter(pk=self.document_type.pk).exists())

    def test_invalid_status_is_rejected_by_validation_and_database(self):
        archive = Archive(
            reference="CT-2026-000200",
            title="Statut invalide",
            category=self.category,
            document_type=self.document_type,
            service=self.service,
            uploaded_by=self.user,
            status="UNKNOWN",
        )
        with self.assertRaises(ValidationError):
            archive.full_clean()

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_archive(reference="CT-2026-000201", status="UNKNOWN")

    def test_invalid_confidentiality_level_is_rejected_by_validation_and_database(self):
        archive = Archive(
            reference="CT-2026-000300",
            title="Confidentialité invalide",
            category=self.category,
            document_type=self.document_type,
            service=self.service,
            uploaded_by=self.user,
            confidentiality_level="TOP_SECRET",
        )
        with self.assertRaises(ValidationError):
            archive.full_clean()

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_archive(reference="CT-2026-000301", confidentiality_level="TOP_SECRET")

    def test_negative_file_size_is_rejected_by_validation_and_database(self):
        archive = Archive(
            reference="CT-2026-000400",
            title="Taille invalide",
            category=self.category,
            document_type=self.document_type,
            service=self.service,
            uploaded_by=self.user,
            file_size=-1,
        )
        with self.assertRaises(ValidationError):
            archive.full_clean()

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_archive(reference="CT-2026-000401", file_size=-1)

    def test_checksum_must_be_empty_or_sha256_hexadecimal(self):
        archive = Archive(
            reference="CT-2026-000500",
            title="Checksum invalide",
            category=self.category,
            document_type=self.document_type,
            service=self.service,
            uploaded_by=self.user,
            checksum="not-a-sha256",
        )
        with self.assertRaises(ValidationError):
            archive.full_clean()

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_archive(reference="CT-2026-000501", checksum="not-a-sha256")

    def test_archive_timestamps_and_dates_are_preserved(self):
        archive = self.create_archive(archived_at=None)

        self.assertEqual(archive.document_date, date(2026, 1, 15))
        self.assertIsNone(archive.archived_at)
        self.assertIsNotNone(archive.created_at)
        self.assertIsNotNone(archive.updated_at)

    def test_archive_string_representation_includes_reference_and_title(self):
        archive = self.create_archive(reference="CT-2026-000600", title="Rapport annuel")

        self.assertEqual(str(archive), "CT-2026-000600 — Rapport annuel")


class ArchiveCrudTests(TestCase):
    """Vérifie le CRUD de métadonnées sous garde technique temporaire T-008."""

    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            username="staff-archives",
            email="staff-archives@example.test",
            password="MotDePasse-Staff-2026",
            is_staff=True,
            role=Role.ADMINISTRATEUR,
        )
        self.role_only_user = user_model.objects.create_user(
            username="role-only",
            email="role-only@example.test",
            password="MotDePasse-Role-2026",
            role=Role.ADMINISTRATEUR,
        )
        self.other_user = user_model.objects.create_user(
            username="other-user",
            email="other-user@example.test",
            password="MotDePasse-Other-2026",
        )
        self.service = Service.objects.create(name="Service actif CRUD")
        self.category = Category.objects.create(name="Catégorie active CRUD")
        self.document_type = DocumentType.objects.create(name="Type actif CRUD")
        self.list_url = "/archives/"
        self.create_url = "/archives/new/"

    def create_archive(self, **overrides):
        defaults = {
            "reference": f"CT-CRUD-{Archive.objects.count() + 1:05d}",
            "title": "Archive de test CRUD",
            "description": "Description de test",
            "category": self.category,
            "document_type": self.document_type,
            "service": self.service,
            "uploaded_by": self.staff,
            "document_date": date(2026, 2, 1),
            "status": ArchiveStatus.ACTIVE,
            "confidentiality_level": ConfidentialityLevel.INTERNAL,
            "file_size": 0,
            "checksum": "",
        }
        defaults.update(overrides)
        return Archive.objects.create(**defaults)

    def payload(self, **overrides):
        data = {
            "reference": "CT-CRUD-POST-00001",
            "title": "Nouvelle archive contrôlée",
            "description": "Description créée via formulaire",
            "category": str(self.category.pk),
            "document_type": str(self.document_type.pk),
            "service": str(self.service.pk),
            "document_date": "2026-02-15",
            "status": ArchiveStatus.ACTIVE,
            "confidentiality_level": ConfidentialityLevel.INTERNAL,
        }
        data.update(overrides)
        return data

    def test_crud_001_anonymous_list_redirects_to_login(self):
        response = self.client.get(self.list_url)

        self.assertRedirects(response, "/accounts/login/?next=/archives/")

    def test_crud_002_consultant_is_denied_from_creation(self):
        self.client.force_login(self.other_user)

        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 403)

    def test_crud_003_staff_can_access_list(self):
        self.client.force_login(self.staff)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)

    def test_crud_004_list_renders_authorized_metadata_only(self):
        archive = self.create_archive(
            reference="CT-CRUD-LIST",
            title="Titre de liste",
            checksum="a" * 64,
        )
        self.client.force_login(self.staff)

        response = self.client.get(self.list_url)

        self.assertContains(response, archive.reference)
        self.assertContains(response, archive.title)
        self.assertNotContains(response, archive.checksum)

    def test_crud_005_valid_post_creates_archive_and_redirects(self):
        self.client.force_login(self.staff)

        response = self.client.post(self.create_url, self.payload())

        archive = Archive.objects.get(reference="CT-CRUD-POST-00001")
        self.assertRedirects(response, f"/archives/{archive.pk}/")
        self.assertEqual(Archive.objects.count(), 1)

    def test_crud_006_create_assigns_uploaded_by_on_server(self):
        self.client.force_login(self.staff)

        self.client.post(self.create_url, self.payload())

        self.assertEqual(
            Archive.objects.get(reference="CT-CRUD-POST-00001").uploaded_by,
            self.staff,
        )

    def test_crud_007_create_ignores_tampered_uploaded_by(self):
        self.client.force_login(self.staff)

        self.client.post(
            self.create_url,
            self.payload(uploaded_by=str(self.other_user.pk)),
        )

        archive = Archive.objects.get(reference="CT-CRUD-POST-00001")
        self.assertEqual(archive.uploaded_by, self.staff)

    def test_crud_008_create_ignores_client_checksum(self):
        client_checksum = "b" * 64
        self.client.force_login(self.staff)

        self.client.post(self.create_url, self.payload(checksum=client_checksum))

        archive = Archive.objects.get(reference="CT-CRUD-POST-00001")
        self.assertEqual(archive.checksum, "")

    def test_crud_009_duplicate_reference_returns_invalid_form(self):
        self.create_archive(reference="CT-CRUD-DUPLICATE")
        self.client.force_login(self.staff)

        response = self.client.post(
            self.create_url,
            self.payload(reference="CT-CRUD-DUPLICATE"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("reference", response.context["form"].errors)
        self.assertEqual(Archive.objects.filter(reference="CT-CRUD-DUPLICATE").count(), 1)

    def test_crud_010_staff_can_view_detail(self):
        archive = self.create_archive()
        self.client.force_login(self.staff)

        response = self.client.get(f"/archives/{archive.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, archive.reference)

    def test_crud_011_staff_can_update_allowed_metadata(self):
        archive = self.create_archive()
        self.client.force_login(self.staff)

        response = self.client.post(
            f"/archives/{archive.pk}/edit/",
            self.payload(
                reference=archive.reference,
                title="Titre modifié",
                description="Description modifiée",
                status=ArchiveStatus.ARCHIVED,
            ),
        )

        self.assertRedirects(response, f"/archives/{archive.pk}/")
        archive.refresh_from_db()
        self.assertEqual(archive.title, "Titre modifié")
        self.assertEqual(archive.status, ArchiveStatus.ARCHIVED)

    def test_crud_012_update_ignores_protected_field_tampering(self):
        original_checksum = "c" * 64
        archive = self.create_archive(
            uploaded_by=self.other_user,
            file_size=128,
            checksum=original_checksum,
        )
        self.client.force_login(self.staff)

        self.client.post(
            f"/archives/{archive.pk}/edit/",
            self.payload(
                reference=archive.reference,
                uploaded_by=str(self.staff.pk),
                checksum="d" * 64,
                file_size="999999",
            ),
        )

        archive.refresh_from_db()
        self.assertEqual(archive.uploaded_by, self.other_user)
        self.assertEqual(archive.checksum, original_checksum)
        self.assertEqual(archive.file_size, 128)

    def test_crud_013_no_physical_delete_route_is_exposed(self):
        archive = self.create_archive()

        with self.assertRaises(Resolver404):
            resolve(f"/archives/{archive.pk}/delete/")

    def test_crud_014_create_post_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)

        response = csrf_client.post(self.create_url, self.payload())

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Archive.objects.filter(reference="CT-CRUD-POST-00001").exists())

    def test_crud_015_update_post_requires_csrf_token(self):
        archive = self.create_archive()
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)

        response = csrf_client.post(
            f"/archives/{archive.pk}/edit/",
            self.payload(reference=archive.reference, title="Tentative sans CSRF"),
        )

        self.assertEqual(response.status_code, 403)
        archive.refresh_from_db()
        self.assertEqual(archive.title, "Archive de test CRUD")

    def test_crud_016_create_form_offers_only_active_references(self):
        inactive_service = Service.objects.create(name="Service inactif CRUD", is_active=False)
        inactive_category = Category.objects.create(name="Catégorie inactive CRUD", is_active=False)
        inactive_type = DocumentType.objects.create(name="Type inactif CRUD", is_active=False)
        self.client.force_login(self.staff)

        response = self.client.get(self.create_url)
        form = response.context["form"]

        self.assertIn(self.service, form.fields["service"].queryset)
        self.assertNotIn(inactive_service, form.fields["service"].queryset)
        self.assertIn(self.category, form.fields["category"].queryset)
        self.assertNotIn(inactive_category, form.fields["category"].queryset)
        self.assertIn(self.document_type, form.fields["document_type"].queryset)
        self.assertNotIn(inactive_type, form.fields["document_type"].queryset)

    def test_crud_017_update_keeps_current_inactive_reference_editable(self):
        inactive_category = Category.objects.create(name="Catégorie historique", is_active=False)
        archive = self.create_archive(category=inactive_category)
        self.client.force_login(self.staff)

        response = self.client.get(f"/archives/{archive.pk}/edit/")
        form = response.context["form"]

        self.assertIn(inactive_category, form.fields["category"].queryset)
        self.assertEqual(response.status_code, 200)

    def test_crud_018_confidentiality_level_is_persisted_without_access_rule(self):
        self.client.force_login(self.staff)

        self.client.post(
            self.create_url,
            self.payload(
                confidentiality_level=ConfidentialityLevel.CONFIDENTIAL,
            ),
        )

        archive = Archive.objects.get(reference="CT-CRUD-POST-00001")
        self.assertEqual(archive.confidentiality_level, ConfidentialityLevel.CONFIDENTIAL)

    def test_crud_019_metadata_is_escaped_in_detail_template(self):
        archive = self.create_archive(title="<script>alert(1)</script>")
        self.client.force_login(self.staff)

        response = self.client.get(f"/archives/{archive.pk}/")

        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;", html=False)
        self.assertNotContains(response, "<script>alert(1)</script>", html=False)

    def test_crud_020_missing_archive_returns_404(self):
        self.client.force_login(self.staff)

        response = self.client.get("/archives/999999/")

        self.assertEqual(response.status_code, 404)


class ArchiveSearchTests(TestCase):
    """Vérifie la recherche GET et les filtres de métadonnées de T-009."""

    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            username="staff-search",
            email="staff-search@example.test",
            password="MotDePasse-Search-2026",
            is_staff=True,
            role=Role.ADMINISTRATEUR,
        )
        self.non_staff = user_model.objects.create_user(
            username="non-staff-search",
            email="non-staff-search@example.test",
            password="MotDePasse-NonStaff-2026",
            role=Role.CONSULTANT,
        )
        self.service = Service.objects.create(name="Service recherche")
        self.other_service = Service.objects.create(name="Autre service recherche")
        self.category = Category.objects.create(name="Catégorie recherche")
        self.other_category = Category.objects.create(name="Autre catégorie recherche")
        self.document_type = DocumentType.objects.create(name="Type recherche")
        self.other_document_type = DocumentType.objects.create(name="Autre type recherche")
        self.list_url = "/archives/"

    def create_archive(self, **overrides):
        defaults = {
            "reference": f"CT-SEARCH-{Archive.objects.count() + 1:05d}",
            "title": "Archive de recherche",
            "description": "Description de recherche",
            "category": self.category,
            "document_type": self.document_type,
            "service": self.service,
            "uploaded_by": self.staff,
            "document_date": date(2026, 3, 15),
            "status": ArchiveStatus.ACTIVE,
            "confidentiality_level": ConfidentialityLevel.INTERNAL,
            "file_size": 0,
            "checksum": "",
        }
        defaults.update(overrides)
        return Archive.objects.create(**defaults)

    def get_as_staff(self, parameters=None):
        self.client.force_login(self.staff)
        return self.client.get(self.list_url, parameters or {})

    def test_search_001_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.list_url, {"q": "contrat"})

        self.assertRedirects(response, "/accounts/login/?next=/archives/%3Fq%3Dcontrat")

    def test_search_002_authenticated_consultant_can_access_search_page(self):
        self.client.force_login(self.non_staff)

        response = self.client.get(self.list_url, {"q": "contrat"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result_count"], 0)

    def test_search_003_staff_user_can_access_search_page(self):
        response = self.get_as_staff()

        self.assertEqual(response.status_code, 200)
        self.assertIn("search_form", response.context)

    def test_search_004_reference_partial_match_returns_archive(self):
        archive = self.create_archive(reference="CT-SEARCH-REFERENCE-PARTIELLE")

        response = self.get_as_staff({"q": "REFERENCE-PART"})

        self.assertContains(response, archive.reference)
        self.assertEqual(response.context["result_count"], 1)

    def test_search_005_title_search_is_case_insensitive(self):
        archive = self.create_archive(title="Rapport Budgétaire Annuel")

        response = self.get_as_staff({"q": "budgétaire"})

        self.assertContains(response, archive.reference)
        self.assertEqual(response.context["result_count"], 1)

    def test_search_006_description_search_returns_archive(self):
        archive = self.create_archive(description="Dossier relatif au matériel informatique")

        response = self.get_as_staff({"q": "matériel informatique"})

        self.assertContains(response, archive.reference)
        self.assertEqual(response.context["result_count"], 1)

    def test_search_007_no_result_displays_the_empty_search_state(self):
        self.create_archive()

        response = self.get_as_staff({"q": "inexistant-total"})

        self.assertEqual(response.context["result_count"], 0)
        self.assertContains(response, "Aucune archive ne correspond aux critères.")

    def test_search_008_category_filter_returns_matching_archives(self):
        matching = self.create_archive(category=self.category)
        self.create_archive(category=self.other_category)

        response = self.get_as_staff({"category": self.category.pk})

        self.assertContains(response, matching.reference)
        self.assertNotContains(response, "CT-SEARCH-00002")
        self.assertEqual(response.context["result_count"], 1)

    def test_search_009_document_type_filter_returns_matching_archives(self):
        matching = self.create_archive(document_type=self.document_type)
        self.create_archive(document_type=self.other_document_type)

        response = self.get_as_staff({"document_type": self.document_type.pk})

        self.assertContains(response, matching.reference)
        self.assertEqual(response.context["result_count"], 1)

    def test_search_010_service_filter_returns_matching_archives(self):
        matching = self.create_archive(service=self.service)
        self.create_archive(service=self.other_service)

        response = self.get_as_staff({"service": self.service.pk})

        self.assertContains(response, matching.reference)
        self.assertEqual(response.context["result_count"], 1)

    def test_search_011_status_filter_supports_active_and_archived_values(self):
        active = self.create_archive(status=ArchiveStatus.ACTIVE)
        archived = self.create_archive(status=ArchiveStatus.ARCHIVED)

        active_response = self.get_as_staff({"status": ArchiveStatus.ACTIVE})
        archived_response = self.get_as_staff({"status": ArchiveStatus.ARCHIVED})

        self.assertContains(active_response, active.reference)
        self.assertNotContains(active_response, archived.reference)
        self.assertContains(archived_response, archived.reference)
        self.assertNotContains(archived_response, active.reference)

    def test_search_012_confidentiality_filter_returns_metadata_without_access_claim(self):
        internal = self.create_archive(confidentiality_level=ConfidentialityLevel.INTERNAL)
        confidential = self.create_archive(
            confidentiality_level=ConfidentialityLevel.CONFIDENTIAL
        )

        response = self.get_as_staff(
            {"confidentiality_level": ConfidentialityLevel.CONFIDENTIAL}
        )

        self.assertContains(response, confidential.reference)
        self.assertNotContains(response, internal.reference)
        self.assertEqual(response.context["result_count"], 1)

    def test_search_013_document_date_from_is_inclusive(self):
        before = self.create_archive(document_date=date(2026, 3, 14))
        matching = self.create_archive(document_date=date(2026, 3, 15))

        response = self.get_as_staff({"document_date_from": "2026-03-15"})

        self.assertContains(response, matching.reference)
        self.assertNotContains(response, before.reference)

    def test_search_014_document_date_to_is_inclusive(self):
        matching = self.create_archive(document_date=date(2026, 3, 15))
        after = self.create_archive(document_date=date(2026, 3, 16))

        response = self.get_as_staff({"document_date_to": "2026-03-15"})

        self.assertContains(response, matching.reference)
        self.assertNotContains(response, after.reference)

    def test_search_015_document_date_interval_is_combined(self):
        before = self.create_archive(document_date=date(2026, 3, 14))
        matching = self.create_archive(document_date=date(2026, 3, 15))
        after = self.create_archive(document_date=date(2026, 3, 16))

        response = self.get_as_staff(
            {"document_date_from": "2026-03-15", "document_date_to": "2026-03-15"}
        )

        self.assertContains(response, matching.reference)
        self.assertNotContains(response, before.reference)
        self.assertNotContains(response, after.reference)

    def test_search_016_invalid_date_interval_displays_form_error(self):
        response = self.get_as_staff(
            {"document_date_from": "2026-03-16", "document_date_to": "2026-03-15"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result_count"], 0)
        self.assertContains(
            response,
            "La date de début doit être antérieure ou égale à la date de fin.",
        )

    def test_search_017_combined_query_service_and_status_filters(self):
        matching = self.create_archive(
            title="Dossier cible combiné",
            service=self.service,
            status=ArchiveStatus.ACTIVE,
        )
        self.create_archive(
            title="Dossier cible mauvais service",
            service=self.other_service,
            status=ArchiveStatus.ACTIVE,
        )
        self.create_archive(
            title="Dossier cible archivé",
            service=self.service,
            status=ArchiveStatus.ARCHIVED,
        )

        response = self.get_as_staff(
            {"q": "Dossier cible", "service": self.service.pk, "status": ArchiveStatus.ACTIVE}
        )

        self.assertContains(response, matching.reference)
        self.assertEqual(response.context["result_count"], 1)

    def test_search_018_pagination_splits_more_than_twenty_results(self):
        for index in range(25):
            self.create_archive(
                reference=f"CT-PAGE-{index:05d}",
                title="Pagination archives",
            )

        first_page = self.get_as_staff({"q": "Pagination archives"})
        second_page = self.get_as_staff({"q": "Pagination archives", "page": 2})

        self.assertEqual(first_page.context["paginator"].count, 25)
        self.assertEqual(len(first_page.context["archives"]), 20)
        self.assertEqual(second_page.context["page_obj"].number, 2)
        self.assertEqual(len(second_page.context["archives"]), 5)

    def test_search_019_pagination_links_preserve_active_filters(self):
        for index in range(21):
            self.create_archive(
                reference=f"CT-PRESERVE-{index:05d}",
                title="Pagination filtrée",
                service=self.service,
                status=ArchiveStatus.ACTIVE,
            )

        response = self.get_as_staff(
            {"q": "Pagination filtrée", "service": self.service.pk, "status": ArchiveStatus.ACTIVE}
        )

        expected_link = (
            f"q=Pagination+filtr%C3%A9e&amp;service={self.service.pk}"
            "&amp;status=ACTIVE&amp;page=2"
        )
        self.assertContains(response, expected_link, html=False)

    def test_search_020_injection_like_query_is_treated_as_plain_text(self):
        self.create_archive(title="Archive légitime")

        response = self.get_as_staff({"q": "' OR 1=1 --"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result_count"], 0)
        self.assertNotContains(response, "Archive légitime")

    def test_search_021_xss_query_is_escaped_in_html(self):
        response = self.get_as_staff({"q": "<script>alert(1)</script>"})

        self.assertContains(
            response, "&lt;script&gt;alert(1)&lt;/script&gt;", html=False
        )
        self.assertNotContains(response, "<script>alert(1)</script>", html=False)

    def test_search_022_results_do_not_expose_checksum_or_password_hash(self):
        archive = self.create_archive(checksum="e" * 64)

        response = self.get_as_staff()

        self.assertContains(response, archive.reference)
        self.assertNotContains(response, archive.checksum)
        self.assertNotContains(response, self.staff.password)

    def test_search_023_empty_query_returns_the_normal_list(self):
        archive = self.create_archive()

        response = self.get_as_staff({"q": ""})

        self.assertContains(response, archive.reference)
        self.assertEqual(response.context["result_count"], 1)

    def test_search_024_null_document_date_does_not_error_with_date_filter(self):
        undated = self.create_archive(document_date=None)
        dated = self.create_archive(document_date=date(2026, 3, 15))

        response = self.get_as_staff({"document_date_from": "2026-03-15"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, dated.reference)
        self.assertNotContains(response, undated.reference)


class ArchiveFileHandlingTests(TestCase):
    """Vérifie le stockage privé et les téléchargements contrôlés de T-010."""

    PDF_CONTENT = b"%PDF-1.4\nsynthetic C-Tech test document\n"

    def setUp(self):
        self.private_media = TemporaryDirectory()
        self.settings_override = override_settings(
            PRIVATE_MEDIA_ROOT=self.private_media.name,
            ARCHIVE_MAX_UPLOAD_SIZE=10 * 1024 * 1024,
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.private_media.cleanup)

        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            username="staff-files",
            email="staff-files@example.test",
            password="MotDePasse-Files-2026",
            is_staff=True,
            role=Role.ADMINISTRATEUR,
        )
        self.non_staff = user_model.objects.create_user(
            username="non-staff-files",
            email="non-staff-files@example.test",
            password="MotDePasse-NonStaffFiles-2026",
            role=Role.CONSULTANT,
        )
        self.service = Service.objects.create(name="Service fichiers")
        self.category = Category.objects.create(name="Catégorie fichiers")
        self.document_type = DocumentType.objects.create(name="Type fichiers")
        self.create_url = "/archives/new/"

    def valid_pdf(self, name="document-demo.pdf"):
        return SimpleUploadedFile(
            name,
            self.PDF_CONTENT,
            content_type="application/pdf",
        )

    def payload(self, **overrides):
        data = {
            "reference": f"CT-FILE-{Archive.objects.count() + 1:05d}",
            "title": "Archive fichier de test",
            "description": "Document synthétique pour tests de sécurité",
            "category": str(self.category.pk),
            "document_type": str(self.document_type.pk),
            "service": str(self.service.pk),
            "document_date": "2026-08-14",
            "status": ArchiveStatus.ACTIVE,
            "confidentiality_level": ConfidentialityLevel.INTERNAL,
        }
        data.update(overrides)
        return data

    def post_create(self, uploaded_file, **overrides):
        self.client.force_login(self.staff)
        return self.client.post(
            self.create_url,
            self.payload(file=uploaded_file, **overrides),
        )

    def create_archive_with_file(self, name="document-demo.pdf", **overrides):
        data = dict(overrides)
        data.setdefault("reference", f"CT-FILE-{Archive.objects.count() + 1:05d}")
        response = self.post_create(self.valid_pdf(name), **data)
        self.assertEqual(response.status_code, 302)
        return Archive.objects.get(reference=data["reference"])

    def private_files(self):
        root = Path(self.private_media.name)
        return [path for path in root.rglob("*") if path.is_file()]

    def test_file_001_valid_upload_creates_private_file_and_real_size(self):
        archive = self.create_archive_with_file()

        self.assertTrue(archive.file.name.startswith("archives/"))
        self.assertTrue(archive.file.storage.exists(archive.file.name))
        self.assertEqual(archive.file_size, len(self.PDF_CONTENT))
        self.assertEqual(archive.checksum, "")

    def test_file_002_uploaded_by_is_always_assigned_on_server(self):
        other_user = get_user_model().objects.create_user(
            username="tampered-owner",
            email="tampered-owner@example.test",
            password="MotDePasse-Tampered-2026",
        )

        archive = self.create_archive_with_file(uploaded_by=str(other_user.pk))

        self.assertEqual(archive.uploaded_by, self.staff)

    def test_file_003_tampered_file_size_is_ignored_for_real_size(self):
        archive = self.create_archive_with_file(file_size="99999999")

        self.assertEqual(archive.file_size, len(self.PDF_CONTENT))

    def test_file_004_disallowed_extension_is_rejected_without_persistence(self):
        response = self.post_create(
            SimpleUploadedFile("payload.exe", b"MZ synthetic", content_type="application/octet-stream")
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("file", response.context["form"].errors)
        self.assertEqual(Archive.objects.count(), 0)
        self.assertEqual(self.private_files(), [])

    def test_file_005_file_larger_than_configured_limit_is_rejected(self):
        with override_settings(ARCHIVE_MAX_UPLOAD_SIZE=10):
            response = self.post_create(self.valid_pdf("large.pdf"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("file", response.context["form"].errors)
        self.assertEqual(Archive.objects.count(), 0)
        self.assertEqual(self.private_files(), [])

    def test_file_006_empty_file_is_rejected(self):
        response = self.post_create(
            SimpleUploadedFile("empty.pdf", b"", content_type="application/pdf")
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("file", response.context["form"].errors)
        self.assertEqual(self.private_files(), [])

    def test_file_007_fake_pdf_with_invalid_signature_is_rejected(self):
        response = self.post_create(
            SimpleUploadedFile(
                "fake.pdf", b"plain text that is not a PDF", content_type="application/pdf"
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("file", response.context["form"].errors)
        self.assertEqual(self.private_files(), [])

    def test_file_008_traversal_filename_cannot_escape_private_root(self):
        archive = self.create_archive_with_file("../../secret.pdf")
        physical_path = Path(archive.file.path).resolve()

        self.assertTrue(physical_path.is_relative_to(Path(self.private_media.name).resolve()))
        self.assertTrue(archive.file.name.startswith("archives/"))
        self.assertNotIn("secret.pdf", archive.file.name)

    def test_file_009_duplicate_original_names_produce_distinct_private_paths(self):
        first = self.create_archive_with_file("rapport.pdf")
        second = self.create_archive_with_file("rapport.pdf")

        self.assertNotEqual(first.file.name, second.file.name)
        self.assertEqual(len(self.private_files()), 2)

    def test_file_010_detail_uses_controlled_download_route_not_public_url(self):
        archive = self.create_archive_with_file()
        self.client.force_login(self.staff)

        response = self.client.get(f"/archives/{archive.pk}/")

        self.assertContains(response, f"/archives/{archive.pk}/download/")
        self.assertNotContains(response, archive.file.name)
        self.assertNotContains(response, "/media/")

    def test_file_011_anonymous_download_redirects_to_login(self):
        archive = self.create_archive_with_file()
        self.client.logout()

        response = self.client.get(f"/archives/{archive.pk}/download/")

        self.assertRedirects(
            response, f"/accounts/login/?next=/archives/{archive.pk}/download/"
        )

    def test_file_012_consultant_cannot_download_internal_archive(self):
        archive = self.create_archive_with_file()
        self.client.force_login(self.non_staff)

        response = self.client.get(f"/archives/{archive.pk}/download/")

        self.assertEqual(response.status_code, 404)

    def test_file_013_staff_download_returns_attachment_and_content(self):
        archive = self.create_archive_with_file()
        self.client.force_login(self.staff)

        response = self.client.get(f"/archives/{archive.pk}/download/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Disposition"].startswith("attachment;"))
        self.assertIn(f"filename=\"{archive.reference}.pdf\"", response["Content-Disposition"])
        self.assertEqual(b"".join(response.streaming_content), self.PDF_CONTENT)

    def test_file_014_unknown_archive_download_returns_404(self):
        self.client.force_login(self.staff)

        response = self.client.get("/archives/999999/download/")

        self.assertEqual(response.status_code, 404)

    def test_file_015_archive_without_file_returns_404_on_download(self):
        archive = Archive.objects.create(
            reference="CT-FILE-WITHOUT-DOCUMENT",
            title="Archive historique sans fichier",
            category=self.category,
            document_type=self.document_type,
            service=self.service,
            uploaded_by=self.staff,
            file_size=0,
        )
        self.client.force_login(self.staff)

        response = self.client.get(f"/archives/{archive.pk}/download/")

        self.assertEqual(response.status_code, 404)

    def test_file_016_missing_physical_file_returns_404_without_deleting_metadata(self):
        archive = self.create_archive_with_file()
        archive.file.storage.delete(archive.file.name)
        self.client.force_login(self.staff)

        response = self.client.get(f"/archives/{archive.pk}/download/")

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Archive.objects.filter(pk=archive.pk).exists())

    def test_file_017_upload_without_csrf_token_is_denied(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)

        response = csrf_client.post(self.create_url, self.payload(file=self.valid_pdf()))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Archive.objects.count(), 0)
        self.assertEqual(self.private_files(), [])

    def test_file_018_update_cannot_replace_existing_document(self):
        archive = self.create_archive_with_file()
        original_name = archive.file.name
        self.client.force_login(self.staff)

        response = self.client.post(
            f"/archives/{archive.pk}/edit/",
            self.payload(
                reference=archive.reference,
                title="Métadonnées modifiées",
                file=self.valid_pdf("replacement.pdf"),
            ),
        )

        self.assertEqual(response.status_code, 302)
        archive.refresh_from_db()
        self.assertEqual(archive.file.name, original_name)
        self.assertEqual(archive.title, "Métadonnées modifiées")
        self.assertEqual(len(self.private_files()), 1)

    def test_file_019_html_like_original_name_is_never_rendered_as_active_markup(self):
        archive = self.create_archive_with_file("<script>alert(1)</script>.pdf")
        self.client.force_login(self.staff)

        response = self.client.get(f"/archives/{archive.pk}/")

        self.assertNotContains(response, "<script>alert(1)</script>", html=False)
        self.assertNotContains(response, archive.file.name)

    def test_file_020_uses_only_synthetic_uploaded_files(self):
        uploaded_file = self.valid_pdf()

        self.assertIsInstance(uploaded_file, SimpleUploadedFile)
        self.assertEqual(uploaded_file.read(), self.PDF_CONTENT)


class ArchiveRbacTests(TestCase):
    """Matrice RBAC provisoire T-011 et protections contre l’inférence."""

    PDF_CONTENT = b"%PDF-1.4\nRBAC synthetic test document\n"

    def setUp(self):
        self.private_media = TemporaryDirectory()
        self.settings_override = override_settings(
            PRIVATE_MEDIA_ROOT=self.private_media.name,
            ARCHIVE_MAX_UPLOAD_SIZE=10 * 1024 * 1024,
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.private_media.cleanup)

        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username="rbac-admin",
            email="rbac-admin@example.test",
            password="MotDePasse-RbacAdmin-2026",
            role=Role.ADMINISTRATEUR,
        )
        self.agent = user_model.objects.create_user(
            username="rbac-agent",
            email="rbac-agent@example.test",
            password="MotDePasse-RbacAgent-2026",
            role=Role.AGENT_ARCHIVES,
        )
        self.consultant = user_model.objects.create_user(
            username="rbac-consultant",
            email="rbac-consultant@example.test",
            password="MotDePasse-RbacConsultant-2026",
            role=Role.CONSULTANT,
        )
        self.superuser = user_model.objects.create_superuser(
            username="rbac-superuser",
            email="rbac-superuser@example.test",
            password="MotDePasse-RbacSuperuser-2026",
        )
        self.service = Service.objects.create(name="Service RBAC")
        self.category = Category.objects.create(name="Catégorie RBAC")
        self.document_type = DocumentType.objects.create(name="Type RBAC")
        self.list_url = "/archives/"
        self.create_url = "/archives/new/"

    def create_archive(self, confidentiality_level, index, **overrides):
        defaults = {
            "reference": f"CT-RBAC-{index:05d}",
            "title": f"Titre {confidentiality_level} RBAC {index}",
            "description": "Archive synthétique de contrôle d’accès",
            "category": self.category,
            "document_type": self.document_type,
            "service": self.service,
            "uploaded_by": self.admin,
            "document_date": date(2026, 8, 14),
            "status": ArchiveStatus.ACTIVE,
            "confidentiality_level": confidentiality_level,
            "file": SimpleUploadedFile(
                f"rbac-{index}.pdf", self.PDF_CONTENT, content_type="application/pdf"
            ),
            "file_size": len(self.PDF_CONTENT),
        }
        defaults.update(overrides)
        return Archive.objects.create(**defaults)

    def create_visibility_set(self):
        return (
            self.create_archive(ConfidentialityLevel.PUBLIC, 1),
            self.create_archive(ConfidentialityLevel.INTERNAL, 2),
            self.create_archive(ConfidentialityLevel.CONFIDENTIAL, 3),
        )

    def payload(self, reference, confidentiality_level, **overrides):
        data = {
            "reference": reference,
            "title": "Archive créée pour RBAC",
            "description": "Création de test RBAC",
            "category": str(self.category.pk),
            "document_type": str(self.document_type.pk),
            "service": str(self.service.pk),
            "document_date": "2026-08-14",
            "status": ArchiveStatus.ACTIVE,
            "confidentiality_level": confidentiality_level,
        }
        data.update(overrides)
        return data

    def get_as(self, user, url, parameters=None):
        self.client.force_login(user)
        return self.client.get(url, parameters or {})

    def test_rbac_001_anonymous_list_redirects_to_login(self):
        response = self.client.get(self.list_url)

        self.assertRedirects(response, "/accounts/login/?next=/archives/")

    def test_rbac_002_admin_list_returns_200(self):
        self.assertEqual(self.get_as(self.admin, self.list_url).status_code, 200)

    def test_rbac_003_agent_list_returns_200(self):
        self.assertEqual(self.get_as(self.agent, self.list_url).status_code, 200)

    def test_rbac_004_consultant_list_returns_200(self):
        self.assertEqual(self.get_as(self.consultant, self.list_url).status_code, 200)

    def test_rbac_005_consultant_list_excludes_internal(self):
        public, internal, _ = self.create_visibility_set()

        response = self.get_as(self.consultant, self.list_url)

        self.assertContains(response, public.reference)
        self.assertNotContains(response, internal.reference)

    def test_rbac_006_consultant_list_excludes_confidential(self):
        public, _, confidential = self.create_visibility_set()

        response = self.get_as(self.consultant, self.list_url)

        self.assertContains(response, public.reference)
        self.assertNotContains(response, confidential.reference)

    def test_rbac_007_agent_list_includes_public(self):
        public = self.create_archive(ConfidentialityLevel.PUBLIC, 1)

        response = self.get_as(self.agent, self.list_url)

        self.assertContains(response, public.reference)

    def test_rbac_008_agent_list_includes_internal(self):
        internal = self.create_archive(ConfidentialityLevel.INTERNAL, 2)

        response = self.get_as(self.agent, self.list_url)

        self.assertContains(response, internal.reference)

    def test_rbac_009_agent_list_excludes_confidential(self):
        confidential = self.create_archive(ConfidentialityLevel.CONFIDENTIAL, 3)

        response = self.get_as(self.agent, self.list_url)

        self.assertNotContains(response, confidential.reference)
        self.assertEqual(response.context["result_count"], 0)

    def test_rbac_010_admin_list_includes_all_confidentiality_levels(self):
        public, internal, confidential = self.create_visibility_set()

        response = self.get_as(self.admin, self.list_url)

        self.assertContains(response, public.reference)
        self.assertContains(response, internal.reference)
        self.assertContains(response, confidential.reference)

    def test_rbac_011_consultant_search_exact_internal_title_returns_no_result(self):
        internal = self.create_archive(ConfidentialityLevel.INTERNAL, 2)

        response = self.get_as(self.consultant, self.list_url, {"q": internal.title})

        self.assertEqual(response.context["result_count"], 0)
        self.assertNotContains(response, internal.reference)

    def test_rbac_012_consultant_search_exact_confidential_title_returns_no_result(self):
        confidential = self.create_archive(ConfidentialityLevel.CONFIDENTIAL, 3)

        response = self.get_as(self.consultant, self.list_url, {"q": confidential.title})

        self.assertEqual(response.context["result_count"], 0)
        self.assertNotContains(response, confidential.reference)

    def test_rbac_013_agent_search_confidential_title_returns_no_result(self):
        confidential = self.create_archive(ConfidentialityLevel.CONFIDENTIAL, 3)

        response = self.get_as(self.agent, self.list_url, {"q": confidential.title})

        self.assertEqual(response.context["result_count"], 0)

    def test_rbac_014_admin_search_confidential_title_returns_result(self):
        confidential = self.create_archive(ConfidentialityLevel.CONFIDENTIAL, 3)

        response = self.get_as(self.admin, self.list_url, {"q": confidential.title})

        self.assertEqual(response.context["result_count"], 1)
        self.assertContains(response, confidential.reference)

    def test_rbac_015_consultant_direct_internal_detail_returns_404(self):
        internal = self.create_archive(ConfidentialityLevel.INTERNAL, 2)

        response = self.get_as(self.consultant, f"/archives/{internal.pk}/")

        self.assertEqual(response.status_code, 404)

    def test_rbac_016_consultant_direct_confidential_detail_returns_404(self):
        confidential = self.create_archive(ConfidentialityLevel.CONFIDENTIAL, 3)

        response = self.get_as(self.consultant, f"/archives/{confidential.pk}/")

        self.assertEqual(response.status_code, 404)

    def test_rbac_017_agent_direct_confidential_detail_returns_404(self):
        confidential = self.create_archive(ConfidentialityLevel.CONFIDENTIAL, 3)

        response = self.get_as(self.agent, f"/archives/{confidential.pk}/")

        self.assertEqual(response.status_code, 404)

    def test_rbac_018_admin_direct_confidential_detail_returns_200(self):
        confidential = self.create_archive(ConfidentialityLevel.CONFIDENTIAL, 3)

        response = self.get_as(self.admin, f"/archives/{confidential.pk}/")

        self.assertEqual(response.status_code, 200)

    def test_rbac_019_consultant_creation_is_forbidden(self):
        self.client.force_login(self.consultant)

        response = self.client.post(
            self.create_url,
            self.payload("CT-RBAC-CREATE-019", ConfidentialityLevel.PUBLIC),
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Archive.objects.filter(reference="CT-RBAC-CREATE-019").exists())

    def test_rbac_020_agent_can_create_public_archive(self):
        self.client.force_login(self.agent)

        response = self.client.post(
            self.create_url,
            self.payload("CT-RBAC-CREATE-020", ConfidentialityLevel.PUBLIC),
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Archive.objects.filter(reference="CT-RBAC-CREATE-020").exists())

    def test_rbac_021_agent_can_create_internal_archive(self):
        self.client.force_login(self.agent)

        response = self.client.post(
            self.create_url,
            self.payload("CT-RBAC-CREATE-021", ConfidentialityLevel.INTERNAL),
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Archive.objects.filter(reference="CT-RBAC-CREATE-021").exists())

    def test_rbac_022_agent_forged_confidential_creation_is_refused(self):
        self.client.force_login(self.agent)

        response = self.client.post(
            self.create_url,
            self.payload("CT-RBAC-CREATE-022", ConfidentialityLevel.CONFIDENTIAL),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("confidentiality_level", response.context["form"].errors)
        self.assertFalse(Archive.objects.filter(reference="CT-RBAC-CREATE-022").exists())

    def test_rbac_023_admin_can_create_confidential_archive(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            self.create_url,
            self.payload("CT-RBAC-CREATE-023", ConfidentialityLevel.CONFIDENTIAL),
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Archive.objects.filter(reference="CT-RBAC-CREATE-023").exists())

    def test_rbac_024_consultant_update_public_archive_is_forbidden(self):
        public = self.create_archive(ConfidentialityLevel.PUBLIC, 1)
        self.client.force_login(self.consultant)

        response = self.client.post(
            f"/archives/{public.pk}/edit/",
            self.payload(public.reference, ConfidentialityLevel.PUBLIC),
        )

        self.assertEqual(response.status_code, 403)

    def test_rbac_025_agent_can_update_public_archive(self):
        public = self.create_archive(ConfidentialityLevel.PUBLIC, 1)
        self.client.force_login(self.agent)

        response = self.client.post(
            f"/archives/{public.pk}/edit/",
            self.payload(
                public.reference,
                ConfidentialityLevel.PUBLIC,
                title="Titre public modifié",
            ),
        )

        self.assertEqual(response.status_code, 302)
        public.refresh_from_db()
        self.assertEqual(public.title, "Titre public modifié")

    def test_rbac_026_agent_can_update_internal_archive(self):
        internal = self.create_archive(ConfidentialityLevel.INTERNAL, 2)
        self.client.force_login(self.agent)

        response = self.client.post(
            f"/archives/{internal.pk}/edit/",
            self.payload(
                internal.reference,
                ConfidentialityLevel.INTERNAL,
                title="Titre interne modifié",
            ),
        )

        self.assertEqual(response.status_code, 302)
        internal.refresh_from_db()
        self.assertEqual(internal.title, "Titre interne modifié")

    def test_rbac_027_agent_direct_confidential_update_returns_404(self):
        confidential = self.create_archive(ConfidentialityLevel.CONFIDENTIAL, 3)

        response = self.get_as(self.agent, f"/archives/{confidential.pk}/edit/")

        self.assertEqual(response.status_code, 404)

    def test_rbac_028_agent_cannot_escalate_public_to_confidential(self):
        public = self.create_archive(ConfidentialityLevel.PUBLIC, 1)
        self.client.force_login(self.agent)

        response = self.client.post(
            f"/archives/{public.pk}/edit/",
            self.payload(public.reference, ConfidentialityLevel.CONFIDENTIAL),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("confidentiality_level", response.context["form"].errors)
        public.refresh_from_db()
        self.assertEqual(public.confidentiality_level, ConfidentialityLevel.PUBLIC)

    def test_rbac_029_consultant_can_download_public_archive(self):
        public = self.create_archive(ConfidentialityLevel.PUBLIC, 1)

        response = self.get_as(self.consultant, f"/archives/{public.pk}/download/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), self.PDF_CONTENT)

    def test_rbac_030_consultant_download_internal_returns_404(self):
        internal = self.create_archive(ConfidentialityLevel.INTERNAL, 2)

        response = self.get_as(self.consultant, f"/archives/{internal.pk}/download/")

        self.assertEqual(response.status_code, 404)

    def test_rbac_031_consultant_download_confidential_returns_404(self):
        confidential = self.create_archive(ConfidentialityLevel.CONFIDENTIAL, 3)

        response = self.get_as(self.consultant, f"/archives/{confidential.pk}/download/")

        self.assertEqual(response.status_code, 404)

    def test_rbac_032_agent_can_download_internal_archive(self):
        internal = self.create_archive(ConfidentialityLevel.INTERNAL, 2)

        response = self.get_as(self.agent, f"/archives/{internal.pk}/download/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), self.PDF_CONTENT)

    def test_rbac_033_agent_download_confidential_returns_404(self):
        confidential = self.create_archive(ConfidentialityLevel.CONFIDENTIAL, 3)

        response = self.get_as(self.agent, f"/archives/{confidential.pk}/download/")

        self.assertEqual(response.status_code, 404)

    def test_rbac_034_admin_can_download_confidential_archive(self):
        confidential = self.create_archive(ConfidentialityLevel.CONFIDENTIAL, 3)

        response = self.get_as(self.admin, f"/archives/{confidential.pk}/download/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), self.PDF_CONTENT)

    def test_rbac_035_consultant_cannot_infer_hidden_archives_from_counts_or_search(self):
        public = self.create_archive(ConfidentialityLevel.PUBLIC, 1)
        confidential_title = "Confidentiel impossible à inférer"
        for index in range(2, 27):
            self.create_archive(
                ConfidentialityLevel.CONFIDENTIAL,
                index,
                title=confidential_title,
            )

        list_response = self.get_as(self.consultant, self.list_url)
        search_response = self.get_as(
            self.consultant, self.list_url, {"q": confidential_title}
        )
        dashboard_response = self.get_as(self.consultant, "/")

        self.assertEqual(list_response.context["result_count"], 1)
        self.assertEqual(list_response.context["paginator"].count, 1)
        self.assertEqual(search_response.context["result_count"], 0)
        self.assertEqual(dashboard_response.context["archive_count"], 1)
        self.assertContains(list_response, public.reference)

    def test_rbac_036_agent_dashboard_excludes_confidential_archives(self):
        self.create_visibility_set()

        response = self.get_as(self.agent, "/")

        self.assertEqual(response.context["archive_count"], 2)

    def test_rbac_037_admin_dashboard_includes_all_archives(self):
        self.create_visibility_set()

        response = self.get_as(self.admin, "/")

        self.assertEqual(response.context["archive_count"], 3)

    def test_rbac_038_technical_superuser_has_full_archive_access(self):
        _, _, confidential = self.create_visibility_set()

        list_response = self.get_as(self.superuser, self.list_url)
        detail_response = self.get_as(self.superuser, f"/archives/{confidential.pk}/")
        download_response = self.get_as(
            self.superuser, f"/archives/{confidential.pk}/download/"
        )

        self.assertContains(list_response, confidential.reference)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(download_response.status_code, 200)

    def test_rbac_039_consultant_navigation_hides_create_and_update_actions(self):
        public = self.create_archive(ConfidentialityLevel.PUBLIC, 1)

        list_response = self.get_as(self.consultant, self.list_url)
        detail_response = self.get_as(self.consultant, f"/archives/{public.pk}/")

        self.assertNotContains(list_response, "Nouvelle archive")
        self.assertNotContains(detail_response, "Modifier")

    def test_rbac_040_agent_navigation_shows_only_authorized_actions(self):
        public = self.create_archive(ConfidentialityLevel.PUBLIC, 1)

        list_response = self.get_as(self.agent, self.list_url)
        detail_response = self.get_as(self.agent, f"/archives/{public.pk}/")

        self.assertContains(list_response, "Nouvelle archive")
        self.assertContains(detail_response, "Modifier")
