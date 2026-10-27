"""Routes racine de la plateforme C-Tech Archives."""

from django.contrib import admin
from django.urls import include, path

from .views import healthz


admin.site.site_header = "C-Tech Archives · Administration technique"
admin.site.site_title = "C-Tech Archives"
admin.site.index_title = "Référentiels et comptes"

urlpatterns = [
    path("", include("dashboard.urls")),
    path("healthz/", healthz, name="healthz"),
    path("accounts/", include("accounts.urls")),
    path("archives/", include("archives.urls")),
    path("audit/", include("audit.urls")),
    path("admin/", admin.site.urls),
]
