"""Garde d’accès technique provisoire pour l’espace documentaire.

Ce garde est volontairement distinct du RBAC métier qui sera défini au ticket
T-011. Il évite toute exposition d’archives à un utilisateur seulement parce
qu’il est authentifié ou possède un rôle métier provisoire.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Autorise temporairement les seuls comptes techniques staff/superuser."""

    def test_func(self):
        user = self.request.user
        return user.is_staff or user.is_superuser

    def handle_no_permission(self):
        """Redirige l’anonyme, mais refuse clairement l’authentifié non staff."""
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()
