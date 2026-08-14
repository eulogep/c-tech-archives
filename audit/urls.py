"""Routes de consultation du journal d’audit."""

from django.urls import path

from .views import AuditLogListView

app_name = "audit"

urlpatterns = [
    path("", AuditLogListView.as_view(), name="list"),
]
