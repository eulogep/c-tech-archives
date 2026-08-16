"""Configuration de l’administration Django pour les utilisateurs C-Tech."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import FutureImprovementVote, User


@admin.register(User)
class CTechUserAdmin(UserAdmin):
    """Administration du modèle personnalisé sans confondre rôle et superutilisateur."""

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "is_staff",
        "date_joined",
    )
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)
    fieldsets = UserAdmin.fieldsets + (
        ("Rôle métier", {"fields": ("role",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Rôle métier", {"fields": ("role",)}),
    )


@admin.register(FutureImprovementVote)
class FutureImprovementVoteAdmin(admin.ModelAdmin):
    """Permet le suivi interne des votes, sans modification de leur intégrité."""

    list_display = ("feature", "user", "created_at")
    list_filter = ("feature",)
    search_fields = ("user__username", "user__email")
    readonly_fields = ("feature", "user", "created_at")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
