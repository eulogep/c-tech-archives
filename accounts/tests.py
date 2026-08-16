"""Tests du modèle utilisateur personnalisé et des rôles métier."""

import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

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


class AuthenticationFlowTests(TestCase):
    """Couvre le parcours d’authentification natif Django du ticket T-006."""

    password = "MotDePasse-Authentification-2026"

    def setUp(self):
        self.user = User.objects.create_user(
            username="auth-user",
            email="auth-user@example.test",
            password=self.password,
        )
        self.login_url = "/accounts/login/"
        self.logout_url = "/accounts/logout/"
        self.home_url = "/"

    def test_auth_001_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.home_url)

        self.assertRedirects(response, f"{self.login_url}?next=/")

    def test_auth_002_valid_user_login_creates_session_and_redirects(self):
        response = self.client.post(
            self.login_url,
            {"username": self.user.username, "password": self.password},
        )

        self.assertRedirects(response, self.home_url)
        self.assertIn("_auth_user_id", self.client.session)

    def test_auth_003_wrong_password_is_refused_with_generic_message(self):
        response = self.client.post(
            self.login_url,
            {"username": self.user.username, "password": "Mauvais-Mot-De-Passe"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Identifiants invalides.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_auth_004_unknown_user_is_refused_with_same_generic_message(self):
        response = self.client.post(
            self.login_url,
            {"username": "inconnu", "password": "Mauvais-Mot-De-Passe"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Identifiants invalides.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_auth_005_inactive_user_is_refused(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            self.login_url,
            {"username": self.user.username, "password": self.password},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Identifiants invalides.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_auth_006_authenticated_user_can_access_protected_view(self):
        self.client.force_login(self.user)

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.username)

    def test_auth_007_logout_invalidates_session_and_protects_home_again(self):
        self.client.force_login(self.user)

        response = self.client.post(self.logout_url)

        self.assertRedirects(response, self.login_url)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertRedirects(self.client.get(self.home_url), f"{self.login_url}?next=/")

    def test_auth_008_login_post_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.get(self.login_url)

        response = csrf_client.post(
            self.login_url,
            {"username": self.user.username, "password": self.password},
        )

        self.assertEqual(response.status_code, 403)

    def test_auth_009_local_next_parameter_is_accepted(self):
        response = self.client.post(
            f"{self.login_url}?next={self.home_url}",
            {"username": self.user.username, "password": self.password, "next": self.home_url},
        )

        self.assertRedirects(response, self.home_url)

    def test_auth_010_external_next_parameter_is_neutralized(self):
        response = self.client.post(
            f"{self.login_url}?next=https://example.invalid/",
            {
                "username": self.user.username,
                "password": self.password,
                "next": "https://example.invalid/",
            },
        )

        self.assertRedirects(response, self.home_url)


class BootstrapDefaultAdminsCommandTests(TestCase):
    """Vérifie le bootstrap explicite, sécurisé et idempotent des comptes privilégiés."""

    steven_email = "steven.bootstrap@example.test"
    steven_password = "Steven-Synthetic-Password-2026"
    euloge_email = "euloge.bootstrap@example.test"
    euloge_password = "Euloge-Synthetic-Password-2026"

    @property
    def environment(self):
        return {
            "CTECH_STEVEN_EMAIL": self.steven_email,
            "CTECH_STEVEN_PASSWORD": self.steven_password,
            "CTECH_EULOGE_EMAIL": self.euloge_email,
            "CTECH_EULOGE_PASSWORD": self.euloge_password,
        }

    def run_command(self, environment=None):
        from io import StringIO

        stdout = StringIO()
        stderr = StringIO()
        with patch.dict(os.environ, environment or self.environment, clear=True):
            call_command("bootstrap_default_admins", stdout=stdout, stderr=stderr)
        return stdout.getvalue(), stderr.getvalue()

    def test_missing_required_variable_fails_without_exposing_values(self):
        for missing_variable in self.environment:
            environment = self.environment.copy()
            missing_value = environment.pop(missing_variable)

            with patch.dict(os.environ, environment, clear=True):
                with self.assertRaisesMessage(CommandError, missing_variable) as context:
                    call_command("bootstrap_default_admins")

            self.assertNotIn(missing_value, str(context.exception))
            self.assertEqual(User.objects.count(), 0)

    def test_bootstrap_configures_business_and_technical_administrators(self):
        self.run_command()

        steven = User.objects.get(email=self.steven_email)
        euloge = User.objects.get(email=self.euloge_email)

        self.assertEqual(steven.username, self.steven_email)
        self.assertEqual(steven.email, self.steven_email)
        self.assertEqual(steven.first_name, "Steven")
        self.assertEqual(steven.last_name, "Parker")
        self.assertEqual(steven.role, Role.ADMINISTRATEUR)
        self.assertTrue(steven.is_active)
        self.assertFalse(steven.is_staff)
        self.assertFalse(steven.is_superuser)
        self.assertNotEqual(steven.password, self.steven_password)
        self.assertTrue(steven.check_password(self.steven_password))

        self.assertEqual(euloge.username, self.euloge_email)
        self.assertEqual(euloge.email, self.euloge_email)
        self.assertEqual(euloge.first_name, "Euloge Junior")
        self.assertEqual(euloge.last_name, "Mabiala")
        self.assertEqual(euloge.role, Role.ADMINISTRATEUR)
        self.assertTrue(euloge.is_active)
        self.assertTrue(euloge.is_staff)
        self.assertTrue(euloge.is_superuser)
        self.assertNotEqual(euloge.password, self.euloge_password)
        self.assertTrue(euloge.check_password(self.euloge_password))

    def test_bootstrap_is_idempotent_and_does_not_create_duplicates(self):
        first_stdout, first_stderr = self.run_command()
        steven = User.objects.get(email=self.steven_email)
        euloge = User.objects.get(email=self.euloge_email)
        initial_ids = {steven.pk, euloge.pk}
        initial_hashes = {steven.pk: steven.password, euloge.pk: euloge.password}

        second_stdout, second_stderr = self.run_command()
        users = User.objects.filter(email__in=[self.steven_email, self.euloge_email])

        self.assertEqual(users.count(), 2)
        self.assertEqual({user.pk for user in users}, initial_ids)
        self.assertEqual(
            {user.pk: user.password for user in users},
            initial_hashes,
        )
        self.assertIn("2 created", first_stdout)
        self.assertIn("2 reconciled", second_stdout)
        self.assertEqual(first_stderr, "")
        self.assertEqual(second_stderr, "")

    def test_existing_accounts_are_reconciled_in_place(self):
        steven_existing = User.objects.create_user(
            username="legacy-steven",
            email=self.steven_email,
            password="Old-Synthetic-Password-2026",
            first_name="Legacy",
            last_name="Account",
            role=Role.CONSULTANT,
            is_active=False,
            is_staff=True,
            is_superuser=True,
        )
        euloge_existing = User.objects.create_user(
            username="legacy-euloge",
            email=self.euloge_email,
            password="Old-Synthetic-Password-2026",
            first_name="Legacy",
            last_name="Technical",
            role=Role.CONSULTANT,
            is_active=False,
            is_staff=False,
            is_superuser=False,
        )

        self.run_command()

        steven = User.objects.get(email=self.steven_email)
        euloge = User.objects.get(email=self.euloge_email)
        self.assertEqual(steven.pk, steven_existing.pk)
        self.assertEqual(steven.username, self.steven_email)
        self.assertEqual(steven.first_name, "Steven")
        self.assertEqual(steven.last_name, "Parker")
        self.assertEqual(steven.role, Role.ADMINISTRATEUR)
        self.assertTrue(steven.is_active)
        self.assertFalse(steven.is_staff)
        self.assertFalse(steven.is_superuser)
        self.assertTrue(steven.check_password(self.steven_password))

        self.assertEqual(euloge.pk, euloge_existing.pk)
        self.assertEqual(euloge.username, self.euloge_email)
        self.assertEqual(euloge.first_name, "Euloge Junior")
        self.assertEqual(euloge.last_name, "Mabiala")
        self.assertEqual(euloge.role, Role.ADMINISTRATEUR)
        self.assertTrue(euloge.is_active)
        self.assertTrue(euloge.is_staff)
        self.assertTrue(euloge.is_superuser)
        self.assertTrue(euloge.check_password(self.euloge_password))

    def test_command_rejects_email_too_long_for_username_without_leaking_value(self):
        username_max_length = User._meta.get_field("username").max_length
        excessive_email = f"{'a' * username_max_length}@example.test"
        environment = self.environment.copy()
        environment["CTECH_STEVEN_EMAIL"] = excessive_email

        with self.assertRaisesMessage(CommandError, "CTECH_STEVEN_EMAIL") as context:
            self.run_command(environment)

        self.assertNotIn(excessive_email, str(context.exception))
        self.assertEqual(User.objects.count(), 0)

    def test_password_whitespace_is_preserved_exactly(self):
        password_with_whitespace = "  Steven-Synthetic-Password-2026  "
        environment = self.environment.copy()
        environment["CTECH_STEVEN_PASSWORD"] = password_with_whitespace

        self.run_command(environment)

        steven = User.objects.get(email=self.steven_email)
        self.assertTrue(steven.check_password(password_with_whitespace))
        self.assertFalse(steven.check_password(password_with_whitespace.strip()))

    def test_command_output_never_leaks_synthetic_passwords(self):
        stdout, stderr = self.run_command()
        output = f"{stdout}\n{stderr}"

        self.assertNotIn(self.steven_password, output)
        self.assertNotIn(self.euloge_password, output)
        self.assertNotIn(self.steven_email, output)
        self.assertNotIn(self.euloge_email, output)

    def test_synthetic_credentials_authenticate_using_configured_emails(self):
        self.run_command()

        self.assertTrue(
            self.client.login(username=self.steven_email, password=self.steven_password)
        )
        self.client.logout()
        self.assertTrue(
            self.client.login(username=self.euloge_email, password=self.euloge_password)
        )


class PrivateProfileAvatarTests(TestCase):
    """Vérifie que l’avatar reste privé, valide et accessible au seul propriétaire."""

    tiny_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\x0dIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00\x05\x00"
        b"\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    def setUp(self):
        self.user = User.objects.create_user(
            username="steven-avatar",
            email="steven.avatar@example.test",
            password="Avatar-Synthetic-Password-2026",
            first_name="Steven",
            last_name="Parker",
            role=Role.ADMINISTRATEUR,
        )
        self.other_user = User.objects.create_user(
            username="other-avatar",
            email="other.avatar@example.test",
            password="Other-Avatar-Synthetic-Password-2026",
        )
        self.profile_url = reverse("profile")
        self.avatar_url = reverse("profile_avatar", args=[self.user.pk])

    def avatar_upload(self):
        return SimpleUploadedFile(
            "steven-profile.png",
            self.tiny_png,
            content_type="image/png",
        )

    def test_avatar_upload_is_stored_in_database_without_public_media_path(self):
        self.client.force_login(self.user)

        response = self.client.post(self.profile_url, {"avatar": self.avatar_upload()})

        self.assertRedirects(response, self.profile_url)
        self.user.refresh_from_db()
        self.assertEqual(bytes(self.user.profile_avatar), self.tiny_png)
        self.assertEqual(self.user.profile_avatar_content_type, "image/png")
        self.assertTrue(self.user.has_profile_avatar)

    def test_avatar_is_only_served_to_its_authenticated_owner_with_private_cache(self):
        self.user.profile_avatar = self.tiny_png
        self.user.profile_avatar_content_type = "image/png"
        self.user.save(update_fields=["profile_avatar", "profile_avatar_content_type"])

        self.client.force_login(self.user)
        response = self.client.get(self.avatar_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, self.tiny_png)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(self.avatar_url).status_code, 404)

    def test_profile_page_renders_private_avatar_route_after_upload(self):
        self.user.profile_avatar = self.tiny_png
        self.user.profile_avatar_content_type = "image/png"
        self.user.save(update_fields=["profile_avatar", "profile_avatar_content_type"])
        self.client.force_login(self.user)

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.avatar_url)
        self.assertContains(response, "Photo de profil de Steven Parker")

    def test_anonymous_user_cannot_access_profile_or_avatar(self):
        self.assertRedirects(
            self.client.get(self.profile_url),
            f"/accounts/login/?next={self.profile_url}",
        )
        self.assertRedirects(
            self.client.get(self.avatar_url),
            f"/accounts/login/?next={self.avatar_url}",
        )


class EmailSignupAndAuthenticationTests(TestCase):
    """Vérifie les parcours e-mail et l’absence d’élévation lors de l’inscription."""

    def setUp(self):
        self.email = "admin.email@example.test"
        self.password = "Secure-Admin-Password-2026!"
        self.admin = User.objects.create_user(
            username=self.email,
            email=self.email,
            password=self.password,
            first_name="Admin",
            last_name="Email",
            role=Role.ADMINISTRATEUR,
            is_staff=True,
        )
        self.login_url = reverse("login")
        self.signup_url = reverse("signup")

    def test_email_login_accepts_case_insensitive_email_and_redirects_on_success(self):
        response = self.client.post(
            self.login_url,
            {"username": self.email.upper(), "password": self.password},
        )

        self.assertRedirects(response, "/")
        self.assertEqual(self.client.session["_auth_user_id"], str(self.admin.pk))

    def test_login_page_labels_identifier_as_email_and_offers_signup(self):
        response = self.client.get(self.login_url)

        self.assertContains(response, "Adresse e-mail")
        self.assertContains(response, "Créer le compte")
        self.assertContains(response, self.signup_url)

    def test_signup_creates_active_consultant_with_email_as_username(self):
        email = "nouveau.consultant@example.test"
        response = self.client.post(
            self.signup_url,
            {
                "email": email,
                "first_name": "Nouveau",
                "last_name": "Consultant",
                "password1": "Nouveau-Consultant-Password-2026!",
                "password2": "Nouveau-Consultant-Password-2026!",
            },
        )

        self.assertRedirects(response, "/")
        user = User.objects.get(email=email)
        self.assertEqual(user.username, email)
        self.assertEqual(user.role, Role.CONSULTANT)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

    def test_signup_ignores_tampered_privilege_fields(self):
        email = "tentative.admin@example.test"
        response = self.client.post(
            self.signup_url,
            {
                "email": email,
                "first_name": "Tentative",
                "last_name": "Admin",
                "password1": "Tentative-Admin-Password-2026!",
                "password2": "Tentative-Admin-Password-2026!",
                "role": Role.ADMINISTRATEUR,
                "is_staff": "true",
                "is_superuser": "true",
            },
        )

        self.assertRedirects(response, "/")
        user = User.objects.get(email=email)
        self.assertEqual(user.role, Role.CONSULTANT)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_signup_rejects_existing_email_even_with_different_case(self):
        response = self.client.post(
            self.signup_url,
            {
                "email": self.email.upper(),
                "password1": "Another-Valid-Password-2026!",
                "password2": "Another-Valid-Password-2026!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Un compte existe déjà pour cette adresse e-mail.")
        self.assertEqual(User.objects.filter(email__iexact=self.email).count(), 1)

    def test_authenticated_user_cannot_create_another_account_from_signup_page(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.signup_url)

        self.assertRedirects(response, "/")


class OnboardingAndFutureImprovementsTests(TestCase):
    """Vérifie les parcours de découverte, sans contourner l’authentification."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="guide.user@example.test",
            email="guide.user@example.test",
            password="Guide-User-Password-2026!",
            role=Role.CONSULTANT,
        )
        self.home_url = reverse("home")
        self.roadmap_url = reverse("future_improvements")

    def test_home_exposes_welcome_guide_and_roadmap_entry_for_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bienvenue, guide.user@example.test")
        self.assertContains(response, "Découvrir l’interface")
        self.assertContains(response, "Guide d’utilisation · étape 1 sur 4")
        self.assertContains(response, self.roadmap_url)
        self.assertContains(response, "onboarding.js")

    def test_future_improvements_is_protected(self):
        response = self.client.get(self.roadmap_url)

        self.assertRedirects(response, f"{reverse('login')}?next={self.roadmap_url}")

    def test_future_improvements_lists_roadmap_for_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.get(self.roadmap_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Futures améliorations")
        self.assertContains(response, "Recherche enrichie et OCR")
        self.assertContains(response, "Sécurité renforcée")
        self.assertContains(response, "Guide d’utilisation")

    def test_roadmap_navigation_is_available_to_consultant_without_privilege_escalation(self):
        self.client.force_login(self.user)

        response = self.client.get(self.home_url)

        self.assertContains(response, "Futures améliorations")
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
