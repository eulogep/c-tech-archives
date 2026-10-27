"""Modèles métier fondamentaux du domaine documentaire C-Tech."""

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from .storage import archive_private_upload_to, private_archive_storage


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

    Le fichier est conservé dans un stockage privé à partir de T-010. L’empreinte
    calculée reste reportée au ticket dédié à l’intégrité.
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
    review_date = models.DateField(
        "prochaine révision",
        null=True,
        blank=True,
        help_text="Date à laquelle le dossier doit être relu ou mis à jour.",
    )
    retention_until = models.DateField(
        "conservation jusqu’au",
        null=True,
        blank=True,
        help_text="Fin de la durée d’utilité administrative : décider ensuite du sort du dossier.",
    )
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
    file = models.FileField(
        "fichier privé",
        storage=private_archive_storage,
        upload_to=archive_private_upload_to,
        blank=True,
        help_text="Document stocké hors de toute exposition publique.",
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
    content_text = models.TextField(
        "texte extrait",
        blank=True,
        editable=False,
        help_text="Texte du document indexé pour la recherche plein texte.",
    )
    search_document = SearchVectorField("index de recherche", null=True, editable=False)
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    updated_at = models.DateTimeField("mise à jour le", auto_now=True)

    class Meta:
        ordering = ("reference",)
        indexes = [
            models.Index(fields=["status", "document_date"], name="archives_status_date_idx"),
            models.Index(fields=["retention_until"], name="archives_retention_idx"),
            models.Index(fields=["review_date"], name="archives_review_idx"),
            GinIndex(fields=["search_document"], name="archives_search_gin"),
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


class ApprovalStatus(models.TextChoices):
    PENDING = "PENDING", "En attente"
    APPROVED = "APPROVED", "Validée"
    REJECTED = "REJECTED", "Refusée"


class ApprovalRequest(models.Model):
    """Demande de validation d’une archive et, une fois décidée, son visa signé.

    Le visa est un HMAC-SHA256 (clé dérivée de SECRET_KEY) portant sur la
    décision et sur une empreinte des métadonnées et du fichier au moment de la
    décision : toute modification ultérieure de l’archive est détectable. Il
    s’agit d’une signature électronique simple, pas d’une signature qualifiée.
    """

    archive = models.ForeignKey(
        Archive, on_delete=models.PROTECT, related_name="approvals", verbose_name="archive"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approval_requests",
        verbose_name="demandée par",
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approvals_to_review",
        verbose_name="valideur",
    )
    message = models.TextField("message", blank=True, max_length=1000)
    status = models.CharField(
        "statut",
        max_length=16,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        db_index=True,
    )
    decision_comment = models.TextField("commentaire de décision", blank=True, max_length=1000)
    decided_at = models.DateTimeField("décidée le", null=True, blank=True)
    signed_fingerprint = models.CharField("empreinte signée", max_length=64, blank=True)
    signature = models.CharField("visa", max_length=64, blank=True)
    created_at = models.DateTimeField("demandée le", auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        constraints = [
            models.UniqueConstraint(
                fields=["archive"],
                condition=Q(status="PENDING"),
                name="archives_one_pending_approval",
            ),
            models.CheckConstraint(
                condition=~Q(approver=models.F("requested_by")),
                name="archives_approval_separation_of_duties",
            ),
        ]
        verbose_name = "demande de validation"
        verbose_name_plural = "demandes de validation"

    def __str__(self) -> str:
        return f"{self.archive.reference} — {self.get_status_display()}"
