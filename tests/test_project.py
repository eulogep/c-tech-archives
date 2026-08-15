"""Tests de fumée pour la configuration du projet Django."""

from django.conf import settings
from django.test import SimpleTestCase


class ProjectConfigurationTests(SimpleTestCase):
    """Vérifie les garanties structurelles des tickets T-001 et T-002."""

    def test_modular_apps_are_registered(self):
        expected_apps = {"accounts", "archives", "audit", "dashboard"}
        self.assertTrue(expected_apps.issubset(set(settings.INSTALLED_APPS)))

    def test_shared_template_and_resource_directories_are_configured(self):
        self.assertIn(settings.BASE_DIR / "templates", settings.TEMPLATES[0]["DIRS"])
        self.assertEqual(settings.STATIC_ROOT, settings.BASE_DIR / "staticfiles")
        self.assertEqual(settings.MEDIA_ROOT, settings.BASE_DIR / "media")

    def test_security_baseline_is_enabled(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertTrue(settings.CSRF_COOKIE_HTTPONLY)
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertEqual(settings.X_FRAME_OPTIONS, "DENY")

    def test_postgresql_is_the_only_application_database(self):
        database = settings.DATABASES["default"]
        self.assertEqual(database["ENGINE"], "django.db.backends.postgresql")
        self.assertTrue(database["NAME"].endswith("c_tech_archives"))
        self.assertEqual(database["USER"], "c_tech_app")
        self.assertEqual(database["HOST"], "127.0.0.1")
        self.assertEqual(database["PORT"], "5432")
        self.assertTrue(database["CONN_HEALTH_CHECKS"])

    def test_hsts_defaults_to_zero_in_local_development(self):
        self.assertEqual(settings.DJANGO_ENV, "development")
        self.assertEqual(settings.SECURE_HSTS_SECONDS, 0)
