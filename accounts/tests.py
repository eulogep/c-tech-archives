"""Tests du modèle utilisateur personnalisé et des rôles métier."""

import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Role, User


class UserModelTests(TestCase):
    """Vérifie les fondations d’authentification et d’autorisation de T-003."""

    def create_user(self, *, username: str, email: str, role: str = Role.CONSULTANT, **extra):
        return User.objects.create_user(
            username=username,
            email=email,
            password="MotDePasse-Test-2026",
            role=role,
            **extra,
        )

    def test_get_user_model_returns_custom_user(self):
        self.assertIs(get_user_model(), User)
        self.assertEqual(get_user_model()._meta.label, "accounts.User")

    def test_valid_user_can_be_created(self):
        user = self.create_user(username="consultant", email="consultant@example.test")

        self.assertEqual(user.role, Role.CONSULTANT)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_superuser)

    def test_password_is_hashed_and_verifiable(self):
        password = "MotDePasse-Securise-2026"
        user = User.objects.create_user(
            username="password-user",
            email="password@example.test",
            password=password,
        )

        self.assertNotEqual(user.password, password)
        self.assertTrue(user.check_password(password))

    def test_administrateur_role_can_be_assigned_without_superuser_privileges(self):
        user = self.create_user(
            username="admin-metier",
            email="admin-metier@example.test",
            role=Role.ADMINISTRATEUR,
        )

        self.assertEqual(user.role, Role.ADMINISTRATEUR)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)

    def test_agent_archives_role_can_be_assigned(self):
        user = self.create_user(
            username="agent-archives",
            email="agent-archives@example.test",
            role=Role.AGENT_ARCHIVES,
        )

        self.assertEqual(user.role, Role.AGENT_ARCHIVES)

    def test_consultant_role_can_be_assigned(self):
        user = self.create_user(
            username="consultant-role",
            email="consultant-role@example.test",
            role=Role.CONSULTANT,
        )

        self.assertEqual(user.role, Role.CONSULTANT)

    def test_invalid_role_is_rejected_by_validation_and_database_constraint(self):
        user = User(
            username="invalid-role",
            email="invalid-role@example.test",
            role="NOT_A_ROLE",
        )
        with self.assertRaises(ValidationError):
            user.full_clean()

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                username="invalid-role-db",
                email="invalid-role-db@example.test",
                password="MotDePasse-Test-2026",
                role="NOT_A_ROLE",
            )

    def test_user_can_be_deactivated(self):
        user = self.create_user(
            username="inactive",
            email="inactive@example.test",
            is_active=False,
        )

        self.assertFalse(user.is_active)

    def test_createsuperuser_command_supports_custom_user_model(self):
        with patch.dict(
            os.environ,
            {"DJANGO_SUPERUSER_PASSWORD": "MotDePasse-Superuser-2026"},
            clear=False,
        ):
            call_command(
                "createsuperuser",
                interactive=False,
                username="root-test",
                email="root-test@example.test",
            )

        superuser = User.objects.get(username="root-test")
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.check_password("MotDePasse-Superuser-2026"))
