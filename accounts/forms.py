"""Formulaires liés au profil utilisateur C-Tech."""

from django import forms
from django.core.exceptions import ValidationError


class ProfileAvatarForm(forms.Form):
    """Accepte une petite image de profil avant stockage privé en base."""

    avatar = forms.ImageField(
        label="Photo de profil",
        help_text="JPEG, PNG ou WebP — 2 Mo maximum.",
    )

    allowed_content_types = {"image/jpeg", "image/png", "image/webp"}
    max_upload_size = 2 * 1024 * 1024

    def clean_avatar(self):
        avatar = self.cleaned_data["avatar"]
        if avatar.content_type not in self.allowed_content_types:
            raise ValidationError("Le format doit être JPEG, PNG ou WebP.")
        if avatar.size > self.max_upload_size:
            raise ValidationError("La photo ne doit pas dépasser 2 Mo.")
        return avatar
