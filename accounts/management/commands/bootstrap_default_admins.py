"""Bootstrap explicite et sécurisé des comptes privilégiés C-Tech.

Cette commande ne s’exécute jamais au démarrage de l’application. Les identités et
mots de passe sont fournis uniquement par les variables d’environnement requises.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction

from accounts.models import Role


@dataclass(frozen=True)
class AccountSpec:
    """Configuration non sensible d’un compte privilégié à réconcilier."""

    email_variable: str
    password_variable: str
    first_name: str
    last_name: str
    is_staff: bool
    is_superuser: bool


ACCOUNT_SPECS = (
    AccountSpec(
        email_variable="CTECH_STEVEN_EMAIL",
        password_variable="CTECH_STEVEN_PASSWORD",
        first_name="Steven",
        last_name="Parker",
        is_staff=False,
        is_superuser=False,
    ),
    AccountSpec(
        email_variable="CTECH_EULOGE_EMAIL",
        password_variable="CTECH_EULOGE_PASSWORD",
        first_name="Euloge Junior",
        last_name="Mabiala",
        is_staff=True,
        is_superuser=True,
    ),
)


def _required_environment_value(variable_name: str, *, strip: bool) -> str:
    """Retourne une variable requise sans jamais exposer sa valeur en erreur."""

    value = os.environ.get(variable_name)
    if value is None:
        raise CommandError(f"Missing required environment variable: {variable_name}")

    normalized_value = value.strip() if strip else value
    if not normalized_value:
        raise CommandError(f"Missing required environment variable: {variable_name}")
    return normalized_value


def _validate_email(email: str, variable_name: str) -> None:
    """Valide l’adresse sans inclure sa valeur dans la sortie d’erreur."""

    try:
        validate_email(email)
    except ValidationError as error:
        raise CommandError(f"Invalid value for environment variable: {variable_name}") from error


def _validate_username_length(email: str, variable_name: str, user_model) -> None:
    """Vérifie que l’email peut être utilisé tel quel comme username Django."""

    username_max_length = user_model._meta.get_field("username").max_length
    if len(email) > username_max_length:
        raise CommandError(
            f"Value for environment variable exceeds username max length: {variable_name}"
        )


class Command(BaseCommand):
    """Crée ou réconcilie explicitement les deux comptes privilégiés C-Tech."""

    help = (
        "Create or reconcile privileged C-Tech accounts from required environment "
        "variables without printing credentials."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        """Applique de manière atomique la configuration attendue aux deux comptes."""

        user_model = get_user_model()
        configured_accounts = []
        for spec in ACCOUNT_SPECS:
            email = _required_environment_value(spec.email_variable, strip=True)
            password = _required_environment_value(spec.password_variable, strip=False)
            _validate_email(email, spec.email_variable)
            _validate_username_length(email, spec.email_variable, user_model)
            configured_accounts.append((spec, email, password))

        if configured_accounts[0][1].lower() == configured_accounts[1][1].lower():
            raise CommandError(
                "Environment variables CTECH_STEVEN_EMAIL and CTECH_EULOGE_EMAIL must differ."
            )

        created_count = 0
        updated_count = 0

        for spec, email, password in configured_accounts:
            username = email
            user = user_model.objects.filter(email__iexact=email).first()

            username_owner = user_model.objects.filter(username=username).first()
            if username_owner is not None and (user is None or username_owner.pk != user.pk):
                raise CommandError(
                    f"Username conflict for environment variable: {spec.email_variable}"
                )

            if user is None:
                user = user_model(email=email, username=username)
                created_count += 1
            else:
                updated_count += 1

            changed_fields = []
            expected_values = {
                "username": username,
                "email": email,
                "first_name": spec.first_name,
                "last_name": spec.last_name,
                "role": Role.ADMINISTRATEUR,
                "is_active": True,
                "is_staff": spec.is_staff,
                "is_superuser": spec.is_superuser,
            }
            for field_name, expected_value in expected_values.items():
                if getattr(user, field_name) != expected_value:
                    setattr(user, field_name, expected_value)
                    changed_fields.append(field_name)

            if not user.check_password(password):
                user.set_password(password)
                changed_fields.append("password")

            if user.pk is None:
                user.save()
            elif changed_fields:
                user.save(update_fields=changed_fields)

        self.stdout.write(
            self.style.SUCCESS(
                f"Privileged accounts bootstrapped: {created_count} created, {updated_count} reconciled."
            )
        )
