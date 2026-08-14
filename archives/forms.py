"""Formulaires explicites du domaine documentaire."""

from pathlib import Path

from django import forms
from django.conf import settings
from django.db.models import Q

from .permissions import (
    can_assign_confidentiality,
    visible_archives_for,
    visible_confidentiality_levels_for,
)
from .models import (
    Archive,
    ArchiveStatus,
    Category,
    ConfidentialityLevel,
    DocumentType,
    Service,
)


class ArchiveForm(forms.ModelForm):
    """Autorise uniquement les métadonnées métier modifiables par un staff.

    `uploaded_by`, `file_size`, `checksum` et les horodatages restent sous
    contrôle serveur et sont donc intentionnellement absents de ce formulaire.
    """

    class Meta:
        model = Archive
        fields = (
            "reference",
            "title",
            "description",
            "category",
            "document_type",
            "service",
            "document_date",
            "status",
            "confidentiality_level",
            "file",
        )
        widgets = {
            "document_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    _CONTENT_TYPES = {
        ".pdf": {"application/pdf"},
        ".doc": {"application/msword"},
        ".docx": {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        },
        ".xls": {"application/vnd.ms-excel"},
        ".xlsx": {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        },
        ".txt": {"text/plain"},
        ".jpg": {"image/jpeg"},
        ".jpeg": {"image/jpeg"},
        ".png": {"image/png"},
    }
    _SIGNATURES = {
        ".pdf": b"%PDF-",
        ".png": b"\x89PNG\r\n\x1a\n",
        ".jpg": b"\xff\xd8\xff",
        ".jpeg": b"\xff\xd8\xff",
    }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self._limit_reference_choices("service", Service)
        self._limit_reference_choices("category", Category)
        self._limit_reference_choices("document_type", DocumentType)
        if self.user is not None:
            allowed_levels = visible_confidentiality_levels_for(self.user)
            self.fields["confidentiality_level"].choices = [
                choice
                for choice in ConfidentialityLevel.choices
                if choice[0] in allowed_levels
            ]
        if self.instance and self.instance.pk:
            self.fields.pop("file", None)

    def clean_confidentiality_level(self):
        confidentiality_level = self.cleaned_data["confidentiality_level"]
        if self.user is not None and not can_assign_confidentiality(
            self.user, confidentiality_level
        ):
            raise forms.ValidationError(
                "Vous ne pouvez pas attribuer ce niveau de confidentialité."
            )
        return confidentiality_level

    def clean_file(self):
        uploaded_file = self.cleaned_data.get("file")
        if not uploaded_file:
            return uploaded_file

        extension = Path(uploaded_file.name).suffix.lower()
        allowed_extensions = {value.lower() for value in settings.ARCHIVE_ALLOWED_EXTENSIONS}
        if extension not in allowed_extensions:
            raise forms.ValidationError("Le type de fichier n’est pas autorisé.")
        if uploaded_file.size <= 0:
            raise forms.ValidationError("Un fichier vide ne peut pas être archivé.")
        if uploaded_file.size > settings.ARCHIVE_MAX_UPLOAD_SIZE:
            raise forms.ValidationError("Le fichier dépasse la taille maximale autorisée.")

        declared_type = uploaded_file.content_type
        expected_types = self._CONTENT_TYPES.get(extension)
        if declared_type and expected_types and declared_type not in expected_types:
            raise forms.ValidationError("Le type déclaré ne correspond pas à l’extension du fichier.")
        if not self._has_expected_signature(uploaded_file, extension):
            raise forms.ValidationError("Le contenu du fichier ne correspond pas au format annoncé.")
        return uploaded_file

    def _has_expected_signature(self, uploaded_file, extension: str) -> bool:
        signature = self._SIGNATURES.get(extension)
        if not signature:
            return True
        position = uploaded_file.tell()
        try:
            uploaded_file.seek(0)
            return uploaded_file.read(len(signature)).startswith(signature)
        finally:
            uploaded_file.seek(position)

    def _limit_reference_choices(self, field_name, model):
        """Propose les valeurs actives, avec la valeur historique courante.

        Lors d’une modification, une archive liée à un référentiel devenu
        inactif reste éditable sans devoir réactiver artificiellement ce
        référentiel ni remplacer sa valeur historique.
        """
        queryset = model.objects.filter(is_active=True)
        if self.instance and self.instance.pk:
            current_id = getattr(self.instance, f"{field_name}_id")
            if current_id:
                queryset = model.objects.filter(Q(is_active=True) | Q(pk=current_id))
        self.fields[field_name].queryset = queryset


class ArchiveSearchForm(forms.Form):
    """Formulaire GET de recherche et filtres, sans modification de modèle."""

    q = forms.CharField(label="Recherche", max_length=255, required=False)
    category = forms.ModelChoiceField(
        label="Catégorie", queryset=Category.objects.none(), required=False
    )
    document_type = forms.ModelChoiceField(
        label="Type documentaire", queryset=DocumentType.objects.none(), required=False
    )
    service = forms.ModelChoiceField(
        label="Service", queryset=Service.objects.none(), required=False
    )
    status = forms.ChoiceField(
        label="Statut",
        choices=[("", "Tous les statuts"), *ArchiveStatus.choices],
        required=False,
    )
    confidentiality_level = forms.ChoiceField(
        label="Confidentialité",
        choices=[("", "Tous les niveaux"), *ConfidentialityLevel.choices],
        required=False,
    )
    document_date_from = forms.DateField(
        label="Date du document à partir du",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    document_date_to = forms.DateField(
        label="Date du document jusqu’au",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        visible_archives = visible_archives_for(user)
        self.fields["category"].queryset = self._searchable_references(
            Category, visible_archives
        )
        self.fields["document_type"].queryset = self._searchable_references(
            DocumentType, visible_archives
        )
        self.fields["service"].queryset = self._searchable_references(
            Service, visible_archives
        )
        allowed_levels = visible_confidentiality_levels_for(user)
        self.fields["confidentiality_level"].choices = [
            ("", "Tous les niveaux"),
            *[
                choice
                for choice in ConfidentialityLevel.choices
                if choice[0] in allowed_levels
            ],
        ]

    @staticmethod
    def _searchable_references(model, visible_archives):
        """Ne propose que les référentiels des archives visibles."""
        return model.objects.filter(archives__in=visible_archives).distinct()

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get("document_date_from")
        date_to = cleaned_data.get("document_date_to")
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError(
                "La date de début doit être antérieure ou égale à la date de fin."
            )
        return cleaned_data
