"""Vues contrôlées de gestion des métadonnées d’archives."""

from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import urlencode
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from audit.context_processors import audit_policy
from audit.models import AuditAction, AuditLog
from audit.services import record_audit_event
from audit.presentation import ACTION_ICONS, ACTION_TONES

from .access import (
    ArchiveCreatePermissionMixin,
    ArchiveUpdatePermissionMixin,
    ArchiveVisibleQuerysetMixin,
)
from .forms import ArchiveForm, ArchiveSearchForm
from .integrity import (
    IntegrityStatus,
    calculate_archive_checksum,
    verify_archive_integrity,
)
from .models import Archive, ConfidentialityLevel
from .permissions import visible_confidentiality_levels_for
from .presentation import PREVIEWABLE_KINDS, file_kind, svg_number


SORT_OPTIONS = {
    "recent": ("Plus récentes", ("-created_at", "-pk")),
    "oldest": ("Plus anciennes", ("created_at", "pk")),
    "document_date": ("Date du document", ("-document_date", "-pk")),
    "reference": ("Référence A → Z", ("reference",)),
    "title": ("Titre A → Z", ("title", "pk")),
}
VIEW_MODES = ("table", "grid")
# Paramètres de présentation : ils ne constituent pas une recherche active.
PRESENTATION_PARAMETERS = ("page", "sort", "view")

TEXT_PREVIEW_LIMIT = 64 * 1024
IMAGE_SIGNATURES = {
    ".png": (b"\x89PNG\r\n\x1a\n", "image/png"),
    ".jpg": (b"\xff\xd8\xff", "image/jpeg"),
    ".jpeg": (b"\xff\xd8\xff", "image/jpeg"),
}


class ArchiveListView(ArchiveVisibleQuerysetMixin, ListView):
    """Liste paginée des archives pour les comptes techniques autorisés."""

    model = Archive
    template_name = "archives/archive_list.html"
    context_object_name = "archives"
    paginate_by = 20

    def get_search_form(self):
        if not hasattr(self, "_search_form"):
            self._search_form = ArchiveSearchForm(
                self.request.GET, user=self.request.user
            )
        return self._search_form

    def get_sort(self):
        sort = self.request.GET.get("sort", "recent")
        return sort if sort in SORT_OPTIONS else "recent"

    def get_view_mode(self):
        view = self.request.GET.get("view", "table")
        return view if view in VIEW_MODES else "table"

    def get_queryset(self):
        queryset = self.visible_archive_queryset(
            Archive.objects.select_related(
                "category", "document_type", "service", "uploaded_by"
            )
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
        return queryset.order_by(*SORT_OPTIONS[self.get_sort()][1])

    def _active_filters(self, form):
        """Décrit chaque critère actif avec le lien qui le retire."""
        if not form.is_valid():
            return []
        filters = []
        for name, field in form.fields.items():
            value = form.cleaned_data.get(name)
            if value in (None, ""):
                continue
            if hasattr(field, "choices") and not hasattr(value, "pk"):
                display = dict(field.choices).get(value, value)
            elif hasattr(value, "strftime"):
                display = value.strftime("%d/%m/%Y")
            else:
                display = str(value)
            parameters = self.request.GET.copy()
            parameters.pop(name, None)
            parameters.pop("page", None)
            filters.append(
                {
                    "label": field.label,
                    "value": display,
                    "remove_query": parameters.urlencode(),
                }
            )
        return filters

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parameters = self.request.GET.copy()
        parameters.pop("page", None)
        search_parameters = {
            key: value
            for key, value in parameters.items()
            if key not in PRESENTATION_PARAMETERS and value
        }
        form = self.get_search_form()
        context["search_form"] = form
        context["query_string"] = parameters.urlencode()
        context["result_count"] = context["paginator"].count
        context["has_active_search"] = bool(search_parameters)
        context["active_filters"] = self._active_filters(form)
        context["advanced_filter_open"] = any(
            key != "q" for key in search_parameters
        )

        sort = self.get_sort()
        view_mode = self.get_view_mode()
        context["sort"] = sort
        context["sort_options"] = [(key, label) for key, (label, _) in SORT_OPTIONS.items()]
        context["view_mode"] = view_mode
        context["view_queries"] = {
            mode: urlencode({**search_parameters, "sort": sort, "view": mode})
            for mode in VIEW_MODES
        }
        if context.get("is_paginated"):
            context["page_links"] = list(
                context["paginator"].get_elided_page_range(
                    context["page_obj"].number, on_each_side=1, on_ends=1
                )
            )

        # Un seul agrégat au lieu de quatre COUNT successifs.
        visible_levels = visible_confidentiality_levels_for(self.request.user)
        counts = self.visible_archive_queryset(Archive.objects.all()).aggregate(
            total=Count("pk"),
            public=Count("pk", filter=Q(confidentiality_level=ConfidentialityLevel.PUBLIC)),
            internal=Count("pk", filter=Q(confidentiality_level=ConfidentialityLevel.INTERNAL)),
            confidential=Count(
                "pk", filter=Q(confidentiality_level=ConfidentialityLevel.CONFIDENTIAL)
            ),
        )
        context["total_visible_count"] = counts["total"]
        context["public_count"] = counts["public"]
        if ConfidentialityLevel.INTERNAL in visible_levels:
            context["internal_count"] = counts["internal"]
        if ConfidentialityLevel.CONFIDENTIAL in visible_levels:
            context["confidential_count"] = counts["confidential"]
        context["visible_levels"] = visible_levels
        context["level_segments"] = _level_segments(counts, visible_levels)
        return context


def _level_segments(counts, visible_levels):
    """Proportions de la barre de périmètre, limitées aux niveaux visibles."""
    keys = {
        ConfidentialityLevel.PUBLIC: "public",
        ConfidentialityLevel.INTERNAL: "internal",
        ConfidentialityLevel.CONFIDENTIAL: "confidential",
    }
    total = counts["total"] or 0
    segments = []
    offset = 0.0
    for value, label in ConfidentialityLevel.choices:
        if value not in visible_levels:
            continue
        count = counts[keys[value]]
        width = (count / total * 100) if total else 0
        segments.append(
            {
                "value": value.lower(),
                "label": label,
                "count": count,
                "x": svg_number(offset),
                "width": svg_number(width),
            }
        )
        offset += width
    return segments


class ArchiveFormContextMixin:
    """Expose les limites d’upload pour la validation anticipée côté navigateur."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["max_upload_size"] = settings.ARCHIVE_MAX_UPLOAD_SIZE
        context["allowed_extensions"] = ",".join(settings.ARCHIVE_ALLOWED_EXTENSIONS)
        return context


class ArchiveCreateView(
    ArchiveCreatePermissionMixin, ArchiveFormContextMixin, SuccessMessageMixin, CreateView
):
    """Crée une archive en imposant l’auteur côté serveur."""

    model = Archive
    form_class = ArchiveForm
    template_name = "archives/archive_form.html"
    success_message = "Archive créée."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        uploaded_file = form.cleaned_data.get("file")
        form.instance.uploaded_by = self.request.user
        form.instance.file_size = uploaded_file.size if uploaded_file else 0
        form.instance.checksum = ""
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                if self.object.file:
                    self.object.checksum = calculate_archive_checksum(self.object)
                    self.object.save(update_fields=["checksum"])
                record_audit_event(
                    actor=self.request.user,
                    action=AuditAction.ARCHIVE_CREATE,
                    request=self.request,
                    archive=self.object,
                    details={"source": "web"},
                )
        except Exception:
            # La base est restaurée par la transaction ; le fichier, lui, a déjà
            # été écrit sur disque et deviendrait orphelin.
            stored_file = getattr(self.object, "file", None)
            if stored_file and stored_file.name:
                stored_file.storage.delete(stored_file.name)
            raise
        return response

    def get_success_url(self):
        return reverse_lazy("archives:detail", kwargs={"pk": self.object.pk})


class ArchiveDetailView(ArchiveVisibleQuerysetMixin, DetailView):
    """Présente les métadonnées de détail sans checksum ni mot de passe."""

    model = Archive
    template_name = "archives/archive_detail.html"
    context_object_name = "archive"

    def get_queryset(self):
        return self.visible_archive_queryset(
            Archive.objects.select_related(
                "category", "document_type", "service", "uploaded_by"
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        archive = self.object
        kind = file_kind(archive.file.name if archive.file else "")
        context["file_kind"] = kind
        context["file_extension"] = (
            Path(archive.file.name).suffix.lstrip(".").upper() if archive.file else ""
        )
        context["can_preview"] = bool(archive.file) and kind in PREVIEWABLE_KINDS
        # Le résultat d’intégrité est une propriété de l’archive : il est montré
        # à tout lecteur autorisé, sans l’identité de la personne qui a vérifié.
        last_check = (
            AuditLog.objects.filter(
                archive=archive, action=AuditAction.ARCHIVE_INTEGRITY_CHECK
            )
            .order_by("-timestamp", "-pk")
            .only("timestamp", "details")
            .first()
        )
        context["last_integrity_check"] = (
            {"timestamp": last_check.timestamp, "result": last_check.details.get("result", "")}
            if last_check
            else None
        )
        context["integrity_state"] = _integrity_state(archive, context["last_integrity_check"])
        if audit_policy(self.request)["audit_policy"]["can_view"]:
            history = list(
                AuditLog.objects.filter(archive=archive).order_by("-timestamp", "-pk")[:8]
            )
            for event in history:
                event.tone = ACTION_TONES.get(event.action, "neutral")
                event.icon = ACTION_ICONS.get(event.action, "dot")
            context["archive_history"] = history
        return context

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        record_audit_event(
            actor=request.user,
            action=AuditAction.ARCHIVE_VIEW,
            request=request,
            archive=self.object,
            details={"source": "web"},
        )
        return response


INTEGRITY_ALERTS = {
    IntegrityStatus.MISMATCH: "Le fichier ne correspond plus à son empreinte.",
    IntegrityStatus.FILE_MISSING: "Le fichier est introuvable dans le stockage privé.",
    IntegrityStatus.ERROR: "La dernière vérification n’a pas pu aboutir.",
}


def _state(tone, glyph, title, detail):
    return {"tone": tone, "glyph": glyph, "title": title, "detail": detail}


def _integrity_state(archive, last_check):
    """Résume l’état d’intégrité affiché dans le panneau D de la fiche."""
    if not archive.file:
        return _state(
            "warning",
            "minus",
            "Aucun fichier",
            "L’intégrité ne peut être vérifiée qu'en présence d'un fichier associé.",
        )
    if not archive.checksum:
        return _state(
            "warning",
            "minus",
            "Empreinte absente",
            "Aucune empreinte de référence n’a été enregistrée pour ce fichier.",
        )
    if last_check is None:
        return _state(
            "unknown",
            "seal",
            "Scellée au dépôt",
            "Empreinte enregistrée, jamais revérifiée depuis.",
        )
    result = last_check["result"]
    if result == IntegrityStatus.VALID:
        return _state(
            "valid",
            "check",
            "Fichier conforme",
            "La dernière vérification correspond à l’empreinte enregistrée.",
        )
    if result in INTEGRITY_ALERTS:
        return _state("alert", "alert", "Alerte d’intégrité", INTEGRITY_ALERTS[result])
    return _state(
        "warning",
        "minus",
        "Vérification incomplète",
        "La dernière vérification n’a pas permis de conclure.",
    )


class ArchiveIntegrityVerifyView(ArchiveVisibleQuerysetMixin, DetailView):
    """Vérifie un fichier visible à la demande sans modifier son checksum."""

    model = Archive

    def get_queryset(self):
        return self.visible_archive_queryset(Archive.objects.all())

    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])

    def post(self, request, *args, **kwargs):
        archive = self.get_object()
        result = verify_archive_integrity(archive)
        record_audit_event(
            actor=request.user,
            action=AuditAction.ARCHIVE_INTEGRITY_CHECK,
            request=request,
            archive=archive,
            details={"result": result.status.value},
        )
        message_by_status = {
            IntegrityStatus.VALID: (
                messages.SUCCESS,
                "Intégrité vérifiée : fichier conforme.",
            ),
            IntegrityStatus.MISMATCH: (
                messages.ERROR,
                "ALERTE : le fichier stocké ne correspond plus à son empreinte enregistrée.",
            ),
            IntegrityStatus.MISSING_CHECKSUM: (
                messages.WARNING,
                "Aucune empreinte de référence n’est disponible.",
            ),
            IntegrityStatus.NO_FILE: (
                messages.WARNING,
                "Aucun fichier n’est associé à cette archive.",
            ),
            IntegrityStatus.FILE_MISSING: (
                messages.ERROR,
                "ALERTE : le fichier associé est introuvable dans le stockage privé.",
            ),
            IntegrityStatus.ERROR: (
                messages.ERROR,
                "La vérification d’intégrité n’a pas pu aboutir.",
            ),
        }
        level, text = message_by_status[result.status]
        messages.add_message(request, level, text)
        return redirect("archives:detail", pk=archive.pk)


class ArchiveDownloadView(ArchiveVisibleQuerysetMixin, DetailView):
    """Diffuse un document privé après contrôle d’accès serveur."""

    model = Archive

    def get_queryset(self):
        return self.visible_archive_queryset(Archive.objects.all())

    def get(self, request, *args, **kwargs):
        archive = self.get_object()
        if not archive.file or not archive.file.storage.exists(archive.file.name):
            raise Http404("Aucun fichier associé à cette archive.")
        try:
            file_handle = archive.file.open("rb")
        except OSError as error:
            raise Http404("Le fichier associé est indisponible.") from error

        record_audit_event(
            actor=request.user,
            action=AuditAction.ARCHIVE_DOWNLOAD,
            request=request,
            archive=archive,
            details={"source": "web"},
        )
        download_name = f"{archive.reference}{Path(archive.file.name).suffix}"
        return FileResponse(file_handle, as_attachment=True, filename=download_name)


class ArchivePreviewView(ArchiveVisibleQuerysetMixin, DetailView):
    """Aperçu à la demande des images et textes, tracé comme un accès au fichier.

    Seuls PNG, JPEG et texte brut sont servis en ligne : la signature est
    revérifiée à la lecture et la réponse est isolée (sandbox, nosniff).
    """

    model = Archive

    def get_queryset(self):
        return self.visible_archive_queryset(Archive.objects.all())

    def get(self, request, *args, **kwargs):
        archive = self.get_object()
        kind = file_kind(archive.file.name if archive.file else "")
        if (
            not archive.file
            or kind not in PREVIEWABLE_KINDS
            or not archive.file.storage.exists(archive.file.name)
        ):
            raise Http404("Aucun aperçu disponible pour cette archive.")

        extension = Path(archive.file.name).suffix.lower()
        try:
            with archive.file.open("rb") as handle:
                if kind == "image":
                    content = handle.read()
                else:
                    content = handle.read(TEXT_PREVIEW_LIMIT + 1)
        except OSError as error:
            raise Http404("Le fichier associé est indisponible.") from error

        if kind == "image":
            signature, content_type = IMAGE_SIGNATURES[extension]
            if not content.startswith(signature):
                raise Http404("Aucun aperçu disponible pour cette archive.")
            response = HttpResponse(content, content_type=content_type)
        else:
            truncated = len(content) > TEXT_PREVIEW_LIMIT
            text = content[:TEXT_PREVIEW_LIMIT].decode("utf-8", errors="replace")
            response = HttpResponse(text, content_type="text/plain; charset=utf-8")
            response["X-Preview-Truncated"] = "true" if truncated else "false"

        record_audit_event(
            actor=request.user,
            action=AuditAction.ARCHIVE_PREVIEW,
            request=request,
            archive=archive,
            details={"source": "web"},
        )
        response["Content-Disposition"] = "inline"
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response


class ArchiveQuickSearchView(ArchiveVisibleQuerysetMixin, View):
    """Recherche instantanée de la palette de commandes, filtrée par le RBAC.

    Ne renvoie que des métadonnées déjà affichées dans la liste ; aucune
    consultation n’est journalisée tant que la fiche n’est pas ouverte.
    """

    limit = 8

    def get(self, request, *args, **kwargs):
        query = request.GET.get("q", "").strip()[:100]
        results = []
        if len(query) >= 2:
            archives = (
                self.visible_archive_queryset(Archive.objects.all())
                .filter(Q(reference__icontains=query) | Q(title__icontains=query))
                .order_by("-created_at", "-pk")
                .only("pk", "reference", "title", "confidentiality_level", "status")[: self.limit]
            )
            results = [
                {
                    "reference": archive.reference,
                    "title": archive.title,
                    "url": reverse("archives:detail", kwargs={"pk": archive.pk}),
                    "level": archive.confidentiality_level.lower(),
                    "level_label": archive.get_confidentiality_level_display(),
                    "status_label": archive.get_status_display(),
                }
                for archive in archives
            ]
        response = JsonResponse({"query": query, "results": results})
        response["Cache-Control"] = "private, no-store"
        return response


class ArchiveUpdateView(
    ArchiveUpdatePermissionMixin, ArchiveFormContextMixin, SuccessMessageMixin, UpdateView
):
    """Modifie les seules métadonnées présentes dans ArchiveForm."""

    model = Archive
    form_class = ArchiveForm
    template_name = "archives/archive_form.html"
    context_object_name = "archive"
    success_message = "Archive modifiée."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        changed_fields = list(form.changed_data)
        with transaction.atomic():
            response = super().form_valid(form)
            if changed_fields:
                record_audit_event(
                    actor=self.request.user,
                    action=AuditAction.ARCHIVE_UPDATE,
                    request=self.request,
                    archive=self.object,
                    details={"changed_fields": changed_fields, "source": "web"},
                )
        return response

    def get_success_url(self):
        return reverse_lazy("archives:detail", kwargs={"pk": self.object.pk})
