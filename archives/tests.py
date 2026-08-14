"""Tests des modèles métier fondamentaux des archives."""

from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase
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

    def test_crud_002_authenticated_non_staff_is_denied_even_with_admin_role(self):
        self.client.force_login(self.role_only_user)

        response = self.client.get(self.list_url)

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
