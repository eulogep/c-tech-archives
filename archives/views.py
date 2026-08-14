"""Vues contrôlées de gestion des métadonnées d’archives."""

from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .access import StaffRequiredMixin
from .forms import ArchiveForm
from .models import Archive


class ArchiveListView(StaffRequiredMixin, ListView):
    """Liste paginée des archives pour les comptes techniques autorisés."""

    model = Archive
    template_name = "archives/archive_list.html"
    context_object_name = "archives"
    paginate_by = 20

    def get_queryset(self):
        return Archive.objects.select_related(
            "category", "document_type", "service", "uploaded_by"
        ).order_by("-created_at")


class ArchiveCreateView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    """Crée une archive en imposant l’auteur côté serveur."""

    model = Archive
    form_class = ArchiveForm
    template_name = "archives/archive_form.html"
    success_message = "Archive créée."

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("archives:detail", kwargs={"pk": self.object.pk})


class ArchiveDetailView(StaffRequiredMixin, DetailView):
    """Présente les métadonnées de détail sans checksum ni mot de passe."""

    model = Archive
    template_name = "archives/archive_detail.html"
    context_object_name = "archive"

    def get_queryset(self):
        return Archive.objects.select_related(
            "category", "document_type", "service", "uploaded_by"
        )


class ArchiveUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    """Modifie les seules métadonnées présentes dans ArchiveForm."""

    model = Archive
    form_class = ArchiveForm
    template_name = "archives/archive_form.html"
    context_object_name = "archive"
    success_message = "Archive modifiée."

    def get_success_url(self):
        return reverse_lazy("archives:detail", kwargs={"pk": self.object.pk})
