"""Vues contrôlées de gestion des métadonnées d’archives."""

from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .access import StaffRequiredMixin
from .forms import ArchiveForm, ArchiveSearchForm
from .models import Archive


class ArchiveListView(StaffRequiredMixin, ListView):
    """Liste paginée des archives pour les comptes techniques autorisés."""

    model = Archive
    template_name = "archives/archive_list.html"
    context_object_name = "archives"
    paginate_by = 20

    def get_search_form(self):
        if not hasattr(self, "_search_form"):
            self._search_form = ArchiveSearchForm(self.request.GET)
        return self._search_form

    def get_queryset(self):
        queryset = Archive.objects.select_related(
            "category", "document_type", "service", "uploaded_by"
        )
        form = self.get_search_form()
        if not form.is_valid():
            return queryset.none()

        cleaned_data = form.cleaned_data
        query = cleaned_data.get("q")
        if query:
            queryset = queryset.filter(
                Q(reference__icontains=query)
                | Q(title__icontains=query)
                | Q(description__icontains=query)
            )
        if category := cleaned_data.get("category"):
            queryset = queryset.filter(category=category)
        if document_type := cleaned_data.get("document_type"):
            queryset = queryset.filter(document_type=document_type)
        if service := cleaned_data.get("service"):
            queryset = queryset.filter(service=service)
        if status := cleaned_data.get("status"):
            queryset = queryset.filter(status=status)
        if confidentiality := cleaned_data.get("confidentiality_level"):
            queryset = queryset.filter(confidentiality_level=confidentiality)
        if date_from := cleaned_data.get("document_date_from"):
            queryset = queryset.filter(document_date__gte=date_from)
        if date_to := cleaned_data.get("document_date_to"):
            queryset = queryset.filter(document_date__lte=date_to)
        return queryset.order_by("-created_at", "-pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parameters = self.request.GET.copy()
        parameters.pop("page", None)
        context["search_form"] = self.get_search_form()
        context["query_string"] = parameters.urlencode()
        context["result_count"] = context["paginator"].count
        context["has_active_search"] = bool(parameters)
        return context


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
