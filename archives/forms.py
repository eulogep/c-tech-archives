"""Formulaires explicites du domaine documentaire."""

from django import forms
from django.db.models import Q

from .models import Archive, Category, DocumentType, Service


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
