"""Administration en lecture seule du journal d’audit."""

from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Expose les événements pour inspection sans permettre leur altération."""

    list_display = (
        "timestamp",
        "actor_identifier",
        "action",
        "archive_reference",
        "ip_address",
    )
    list_filter = ("action",)
    search_fields = ("actor_identifier", "archive_reference")
    ordering = ("-timestamp", "-pk")
    readonly_fields = (
        "actor",
        "actor_identifier",
        "action",
        "archive",
        "archive_reference",
        "timestamp",
        "ip_address",
        "details",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
