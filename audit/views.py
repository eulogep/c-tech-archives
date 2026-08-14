"""Consultation métier contrôlée du journal d’audit."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import ListView

from django.db.models import Q

from accounts.models import Role

from .models import AuditAction, AuditLog


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
        queryset = AuditLog.objects.select_related("actor", "archive")
        action = self.request.GET.get("action", "").strip()
        query = self.request.GET.get("q", "").strip()

        if action and action in AuditAction.values:
            queryset = queryset.filter(action=action)
        if query:
            queryset = queryset.filter(
                Q(actor_identifier__icontains=query)
                | Q(archive_reference__icontains=query)
                | Q(ip_address__icontains=query)
            )
        return queryset.order_by("-timestamp", "-pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parameters = self.request.GET.copy()
        parameters.pop("page", None)
        context["query_string"] = parameters.urlencode()
        context["has_active_search"] = bool(parameters)
        context["action_filter"] = self.request.GET.get("action", "").strip()
        context["q_filter"] = self.request.GET.get("q", "").strip()
        context["available_actions"] = AuditAction.choices
        context["total_event_count"] = AuditLog.objects.count()
        return context

