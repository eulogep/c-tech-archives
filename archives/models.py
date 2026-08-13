"""Modèles métier fondamentaux du domaine documentaire C-Tech."""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class ActiveNamedModel(models.Model):
    """Référentiel simple conservant son historique lorsqu’il devient inactif."""

    name = models.CharField("nom", max_length=150, unique=True)
    description = models.TextField("description", blank=True)
    is_active = models.BooleanField("actif", default=True)
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("mis à jour le", auto_now=True)

    class Meta:
        abstract = True
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Service(ActiveNamedModel):
    """Service organisationnel propriétaire ou destinataire d’archives."""

    class Meta(ActiveNamedModel.Meta):
        verbose_name = "service"
        verbose_name_plural = "services"


class Category(ActiveNamedModel):
    """Classement documentaire général, distinct du type métier précis."""

    class Meta(ActiveNamedModel.Meta):
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"


class DocumentType(ActiveNamedModel):
    """Type documentaire précis, distinct de la catégorie générale."""

    class Meta(ActiveNamedModel.Meta):
        verbose_name = "type de document"
        verbose_name_plural = "types de document"


class ArchiveStatus(models.TextChoices):
    """États documentaires minimaux, sans workflow complexe à ce stade."""

    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archivée"


class ConfidentialityLevel(models.TextChoices):
    """Niveaux provisoires à confirmer avec C-Tech, sans permission associée."""

    PUBLIC = "PUBLIC", "Public"
    INTERNAL = "INTERNAL", "Interne"
    CONFIDENTIAL = "CONFIDENTIAL", "Confidentiel"


class Archive(models.Model):
    """Entité centrale regroupant les métadonnées d’un document archivé.

    Le champ de fichier et l’empreinte calculée seront intégrés dans les tickets
    dédiés au téléversement ; T-004 conserve uniquement les métadonnées utiles.
    """

    reference = models.CharField("référence", max_length=32, unique=True)
    title = models.CharField("titre", max_length=255)
    description = models.TextField("description", blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="archives",
        verbose_name="catégorie",
    )
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        related_name="archives",
        verbose_name="type de document",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="archives",
        verbose_name="service",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_archives",
        verbose_name="ajoutée par",
    )
    document_date = models.DateField("date du document", null=True, blank=True)
    archived_at = models.DateTimeField("date d’archivage", null=True, blank=True)
    status = models.CharField(
        "statut",
        max_length=16,
        choices=ArchiveStatus.choices,
        default=ArchiveStatus.ACTIVE,
    )
    confidentiality_level = models.CharField(
        "niveau de confidentialité",
        max_length=16,
        choices=ConfidentialityLevel.choices,
        default=ConfidentialityLevel.INTERNAL,
    )
    file_size = models.PositiveBigIntegerField(
        "taille du fichier (octets)",
        default=0,
        validators=[MinValueValidator(0)],
    )
    checksum = models.CharField(
        "empreinte SHA-256",
        max_length=64,
        blank=True,
        help_text="Empreinte SHA-256 hexadécimale, renseignée par un futur ticket d’upload.",
    )
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    updated_at = models.DateTimeField("mise à jour le", auto_now=True)

    class Meta:
        ordering = ("reference",)
        indexes = [
            models.Index(fields=["status", "document_date"], name="archives_status_date_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=ArchiveStatus.values),
                name="archives_archive_status_is_valid",
            ),
            models.CheckConstraint(
                condition=Q(confidentiality_level__in=ConfidentialityLevel.values),
                name="archives_archive_confidentiality_is_valid",
            ),
            models.CheckConstraint(
                condition=Q(file_size__gte=0),
                name="archives_archive_file_size_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(checksum="") | Q(checksum__regex=r"^[0-9A-Fa-f]{64}$"),
                name="archives_archive_checksum_is_sha256_or_empty",
            ),
        ]
        verbose_name = "archive"
        verbose_name_plural = "archives"

    def __str__(self) -> str:
        return f"{self.reference} — {self.title}"
