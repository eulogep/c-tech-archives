"""Tests des modèles métier fondamentaux des archives."""

from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

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
