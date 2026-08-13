"""Tests de fumée pour l’initialisation du projet Django."""

from django.conf import settings
from django.test import SimpleTestCase


class ProjectConfigurationTests(SimpleTestCase):
    """Vérifie les garanties structurelles introduites par T-001."""

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
