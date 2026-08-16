"""Modèles d’authentification et d’autorisation de la plateforme C-Tech."""

from django.contrib.auth.models import AbstractUser
from django.core.validators import validate_email
from django.db import models


class Role(models.TextChoices):
    """Rôles métier principaux, distincts des permissions et privilèges Django."""

    ADMINISTRATEUR = "ADMINISTRATEUR", "Administrateur"
    AGENT_ARCHIVES = "AGENT_ARCHIVES", "Agent d’archives"
    CONSULTANT = "CONSULTANT", "Consultant"


class FutureImprovementFeature(models.TextChoices):
    """Fonctionnalités affichées dans la feuille de route participative."""

    SEARCH_OCR = "SEARCH_OCR", "Recherche enrichie et OCR"
    SIGNATURE = "SIGNATURE", "Validation et signature électronique"
    RETENTION = "RETENTION", "Calendrier de conservation"
    ANALYTICS = "ANALYTICS", "Indicateurs et rapports"
    SECURITY = "SECURITY", "Sécurité renforcée"
    CONNECTORS = "CONNECTORS", "Connecteurs métier"


class User(AbstractUser):
    """Utilisateur C-Tech utilisant le système d’authentification natif de Django.

    Le champ ``username`` est conservé comme identifiant technique du MVP. L’adresse
    électronique reste obligatoire et unique afin de faciliter les évolutions futures
    sans modifier inutilement le flux d’authentification Django à ce stade. L’avatar
    éventuel est conservé en base de données afin de ne pas exposer un fichier personnel
    sous une URL publique.
    """

    email = models.EmailField(
        "adresse électronique",
        unique=True,
        validators=[validate_email],
    )
    role = models.CharField(
        "rôle métier",
        max_length=20,
        choices=Role.choices,
        default=Role.CONSULTANT,
        db_index=True,
    )
    profile_avatar = models.BinaryField(
        "avatar privé",
        null=True,
        blank=True,
        editable=False,
    )
    profile_avatar_content_type = models.CharField(
        "type MIME de l’avatar",
        max_length=100,
        blank=True,
        editable=False,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=Role.values),
                name="accounts_user_role_is_valid",
            )
        ]
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    @property
    def has_profile_avatar(self) -> bool:
        """Indique si un avatar privé exploitable est associé à l’utilisateur."""
        return bool(self.profile_avatar and self.profile_avatar_content_type)

    def __str__(self) -> str:
        return self.get_full_name() or self.username


class FutureImprovementVote(models.Model):
    """Vote d’un utilisateur authentifié pour une amélioration identifiée."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="future_improvement_votes",
    )
    feature = models.CharField(max_length=32, choices=FutureImprovementFeature.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "feature"),
                name="accounts_unique_future_improvement_vote",
            )
        ]
        ordering = ("-created_at",)
        verbose_name = "vote pour une amélioration future"
        verbose_name_plural = "votes pour les améliorations futures"

    def __str__(self) -> str:
        return f"{self.user} → {self.get_feature_display()}"
