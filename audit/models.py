"""Modèle append-only du journal d’audit métier."""

from django.conf import settings
from django.db import models


class AuditAction(models.TextChoices):
    """Événements métier effectivement disponibles dans le MVP."""

    LOGIN = "LOGIN", "Connexion réussie"
    LOGOUT = "LOGOUT", "Déconnexion"
    ARCHIVE_CREATE = "ARCHIVE_CREATE", "Création d’archive"
    ARCHIVE_UPDATE = "ARCHIVE_UPDATE", "Modification d’archive"
    ARCHIVE_VIEW = "ARCHIVE_VIEW", "Consultation d’archive"
    ARCHIVE_DOWNLOAD = "ARCHIVE_DOWNLOAD", "Téléchargement d’archive"
    ARCHIVE_INTEGRITY_CHECK = "ARCHIVE_INTEGRITY_CHECK", "Vérification d’intégrité"
    ARCHIVE_PREVIEW = "ARCHIVE_PREVIEW", "Aperçu d’archive"
    AUDIT_EXPORT = "AUDIT_EXPORT", "Export du journal d’audit"
    PASSWORD_CHANGE = "PASSWORD_CHANGE", "Changement de mot de passe"
    ARCHIVE_EXPORT = "ARCHIVE_EXPORT", "Export des archives"
    TWO_FACTOR_ENABLE = "TWO_FACTOR_ENABLE", "Activation de la double authentification"
    TWO_FACTOR_DISABLE = "TWO_FACTOR_DISABLE", "Désactivation de la double authentification"
    TWO_FACTOR_FAILURE = "TWO_FACTOR_FAILURE", "Échec de double authentification"
    RECOVERY_CODE_USED = "RECOVERY_CODE_USED", "Code de secours utilisé"


class AuditLog(models.Model):
    """Trace métier structurée créée exclusivement par les services applicatifs."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audit_events",
        verbose_name="acteur",
    )
    actor_identifier = models.CharField("identifiant acteur", max_length=150)
    action = models.CharField("action", max_length=32, choices=AuditAction.choices)
    archive = models.ForeignKey(
        "archives.Archive",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="audit_events",
        verbose_name="archive",
    )
    archive_reference = models.CharField(
        "référence archive", max_length=100, blank=True
    )
    timestamp = models.DateTimeField("horodatage", auto_now_add=True)
    ip_address = models.GenericIPAddressField(
        "adresse IP", null=True, blank=True, unpack_ipv4=True
    )
    details = models.JSONField("détails minimaux", default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp", "-pk"]
        indexes = [
            models.Index(fields=["-timestamp", "-id"], name="audit_timestamp_idx"),
            models.Index(fields=["action", "-timestamp"], name="audit_action_timestamp_idx"),
        ]
        verbose_name = "événement d’audit"
        verbose_name_plural = "événements d’audit"

    def __str__(self) -> str:
        return f"{self.get_action_display()} — {self.actor_identifier} — {self.timestamp:%Y-%m-%d %H:%M:%S}"
