"""Administration Django du domaine documentaire C-Tech."""

from django.contrib import admin

from .models import Archive, Category, DocumentType, Service


class ActiveNamedModelAdmin(admin.ModelAdmin):
    """Configuration commune des référentiels documentaires actifs/inactifs."""

    list_display = ("name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    ordering = ("name",)


@admin.register(Service)
class ServiceAdmin(ActiveNamedModelAdmin):
    pass


@admin.register(Category)
class CategoryAdmin(ActiveNamedModelAdmin):
    pass


@admin.register(DocumentType)
class DocumentTypeAdmin(ActiveNamedModelAdmin):
    pass


@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    """Vue d’administration centrée sur les métadonnées, pas sur un back-office complet."""

    list_display = (
        "reference",
        "title",
        "category",
        "document_type",
        "service",
        "status",
        "confidentiality_level",
        "uploaded_by",
        "document_date",
        "archived_at",
    )
    list_filter = (
        "status",
        "confidentiality_level",
        "category",
        "document_type",
        "service",
    )
    search_fields = ("reference", "title", "description")
    autocomplete_fields = ("category", "document_type", "service", "uploaded_by")
    ordering = ("reference",)
    readonly_fields = ("created_at", "updated_at")
