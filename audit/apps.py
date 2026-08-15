from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "audit"

    def ready(self):
        """Enregistre les signaux d’authentification une seule fois au démarrage."""
        from . import signals  # noqa: F401
