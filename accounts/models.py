"""Modèles d’authentification et d’autorisation de la plateforme C-Tech."""

from django.contrib.auth.models import AbstractUser
from django.core.validators import validate_email
from django.db import models


class Role(models.TextChoices):
    """Rôles métier principaux, distincts des permissions et privilèges Django."""

    ADMINISTRATEUR = "ADMINISTRATEUR", "Administrateur"
    AGENT_ARCHIVES = "AGENT_ARCHIVES", "Agent d’archives"
    CONSULTANT = "CONSULTANT", "Consultant"


class User(AbstractUser):
    """Utilisateur C-Tech utilisant le système d’authentification natif de Django.

    Le champ ``username`` est conservé comme identifiant technique du MVP. L’adresse
    électronique reste obligatoire et unique afin de faciliter les évolutions futures
    sans modifier inutilement le flux d’authentification Django à ce stade.
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

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=Role.values),
                name="accounts_user_role_is_valid",
            )
        ]
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def __str__(self) -> str:
        return self.get_full_name() or self.username
