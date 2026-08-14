"""Formulaires explicites du domaine documentaire."""

from django import forms
from django.db.models import Q

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
        )
        widgets = {
            "document_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._limit_reference_choices("service", Service)
        self._limit_reference_choices("category", Category)
        self._limit_reference_choices("document_type", DocumentType)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = self._searchable_references(Category)
        self.fields["document_type"].queryset = self._searchable_references(
            DocumentType
        )
        self.fields["service"].queryset = self._searchable_references(Service)

    @staticmethod
    def _searchable_references(model):
        """Inclut les référentiels actifs et historiques utilisés par une archive."""
        return model.objects.filter(
            Q(is_active=True) | Q(archives__isnull=False)
        ).distinct()

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get("document_date_from")
        date_to = cleaned_data.get("document_date_to")
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError(
                "La date de début doit être antérieure ou égale à la date de fin."
            )
        return cleaned_data
