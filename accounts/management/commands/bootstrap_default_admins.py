"""Bootstrap explicite et sécurisé des comptes privilégiés C-Tech.

Les identités et mots de passe sont fournis uniquement par les variables
d’environnement requises. Deux modes :

- réconciliation (par défaut) : crée les comptes manquants et réaligne les
  comptes existants, mot de passe et activation compris ;
- ``--create-only`` (utilisé au démarrage Render) : crée les comptes manquants
  sans jamais modifier un compte existant. Un administrateur désactivé reste
  désactivé et un mot de passe changé n’est pas écrasé à chaque redémarrage.
  ``CTECH_BOOTSTRAP_RECONCILE=true`` rétablit ponctuellement la réconciliation
  sur un hébergement sans shell.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
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


def _validate_password_strength(password: str, variable_name: str, user) -> None:
    """Applique AUTH_PASSWORD_VALIDATORS sans jamais afficher le mot de passe."""

    try:
        validate_password(password, user)
    except ValidationError as error:
        raise CommandError(
            f"Password from environment variable is too weak: {variable_name}"
        ) from error


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


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

    def add_arguments(self, parser):
        parser.add_argument(
            "--create-only",
            action="store_true",
            help="Create missing accounts but never modify existing ones.",
        )
        parser.add_argument(
            "--allow-missing",
            action="store_true",
            help="Skip with a warning instead of failing when variables are missing.",
        )

    def handle(self, *args, **options):
        create_only = options["create_only"] and not _env_flag("CTECH_BOOTSTRAP_RECONCILE")
        try:
            created_count, updated_count, skipped_count = self._bootstrap(create_only)
        except CommandError as error:
            if options["allow_missing"] and str(error).startswith(
                "Missing required environment variable"
            ):
                self.stderr.write(f"Privileged account bootstrap skipped: {error}")
                return
            raise

        mode = "create-only" if create_only else "reconcile"
        self.stdout.write(
            self.style.SUCCESS(
                f"Privileged accounts bootstrapped ({mode}): {created_count} created, "
                f"{updated_count} reconciled, {skipped_count} left unchanged."
            )
        )

    @transaction.atomic
    def _bootstrap(self, create_only: bool):
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
        skipped_count = 0

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
            elif create_only:
                skipped_count += 1
                continue
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
                _validate_password_strength(password, spec.password_variable, user)
                user.set_password(password)
                changed_fields.append("password")

            if user.pk is None:
                user.save()
            elif changed_fields:
                user.save(update_fields=changed_fields)

        return created_count, updated_count, skipped_count
