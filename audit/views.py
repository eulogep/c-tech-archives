"""Consultation métier contrôlée du journal d’audit."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import ListView

from accounts.models import Role

from .models import AuditLog


class AuditLogListView(LoginRequiredMixin, ListView):
    """Affiche les événements d’audit aux seuls administrateurs autorisés."""

    model = AuditLog
    template_name = "audit/audit_log_list.html"
    context_object_name = "events"
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not (
            request.user.is_superuser or request.user.role == Role.ADMINISTRATEUR
        ):
            raise PermissionDenied(
                "La consultation du journal d’audit est réservée aux administrateurs."
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return AuditLog.objects.select_related("actor", "archive").order_by(
            "-timestamp", "-pk"
        )
