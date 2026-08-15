"""Routes de gestion contrôlée des métadonnées d’archives."""

from django.urls import path

from . import views

app_name = "archives"

urlpatterns = [
    path("", views.ArchiveListView.as_view(), name="list"),
    path("new/", views.ArchiveCreateView.as_view(), name="create"),
    path("<int:pk>/", views.ArchiveDetailView.as_view(), name="detail"),
    path("<int:pk>/download/", views.ArchiveDownloadView.as_view(), name="download"),
    path(
        "<int:pk>/verify-integrity/",
        views.ArchiveIntegrityVerifyView.as_view(),
        name="verify_integrity",
    ),
    path("<int:pk>/edit/", views.ArchiveUpdateView.as_view(), name="update"),
]
