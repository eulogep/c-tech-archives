"""Formulaires liés à l’authentification et au profil privé C-Tech."""

from __future__ import annotations

import warnings
from io import BytesIO

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from PIL import Image

from .models import Role, User


class EmailAuthenticationForm(AuthenticationForm):
    """Formulaire de connexion dont l’identifiant visible est l’adresse e-mail."""

    username = forms.CharField(
        label="Adresse e-mail",
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "autofocus": True,
                "placeholder": "nom@exemple.com",
            }
        ),
    )

    def clean_username(self):
        """Normalise l’identifiant sans modifier le mot de passe."""

        return self.cleaned_data["username"].strip().lower()


class SignUpForm(forms.Form):
    """Crée exclusivement un compte Consultant, sans champ de rôle modifiable."""

    email = forms.EmailField(
        label="Adresse e-mail",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "nom@exemple.com"}),
    )
    first_name = forms.CharField(label="Prénom", max_length=150, required=False)
    last_name = forms.CharField(label="Nom", max_length=150, required=False)
    password1 = forms.CharField(
        label="Mot de passe",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirmation du mot de passe",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_email(self):
        """Garantit un identifiant technique égal à une adresse e-mail unique."""

        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Un compte existe déjà pour cette adresse e-mail.")
        if len(email) > User._meta.get_field("username").max_length:
            raise ValidationError("Cette adresse e-mail est trop longue pour créer un compte.")
        return email

    def clean_password2(self):
        """Vérifie la confirmation puis applique les règles Django de mot de passe."""

        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data["password2"]
        if password1 and password1 != password2:
            raise ValidationError("Les deux mots de passe ne correspondent pas.")

        user = User(
            email=self.cleaned_data.get("email", ""),
            username=self.cleaned_data.get("email", ""),
            first_name=self.cleaned_data.get("first_name", ""),
            last_name=self.cleaned_data.get("last_name", ""),
        )
        validate_password(password2, user)
        return password2

    def save(self) -> User:
        """Crée un consultant actif ; l’élévation de rôle reste une action administrative."""

        email = self.cleaned_data["email"]
        return User.objects.create_user(
            username=email,
            email=email,
            password=self.cleaned_data["password1"],
            first_name=self.cleaned_data["first_name"].strip(),
            last_name=self.cleaned_data["last_name"].strip(),
            role=Role.CONSULTANT,
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )


class ProfileAvatarForm(forms.Form):
    """Accepte une petite image de profil avant stockage privé en base."""

    avatar = forms.FileField(
        label="Photo de profil",
        help_text="JPEG, PNG ou WebP — 2 Mo maximum.",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )

    allowed_content_types = {
        "image/jpeg": "JPEG",
        "image/png": "PNG",
        "image/webp": "WEBP",
    }
    canonical_content_types = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
    }
    extensions_by_format = {
        "JPEG": {"jpg", "jpeg"},
        "PNG": {"png"},
        "WEBP": {"webp"},
    }
    allowed_pillow_formats = ("JPEG", "PNG", "WEBP")
    max_upload_size = 2 * 1024 * 1024
    max_dimension = 4096
    max_pixels = 16_777_216

    @staticmethod
    def _format_from_signature(header: bytes) -> str | None:
        """Identifie les trois signatures autorisées sans appeler Pillow."""

        if header.startswith(b"\xff\xd8\xff"):
            return "JPEG"
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "PNG"
        if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
            return "WEBP"
        return None

    def clean_avatar(self):
        avatar = self.cleaned_data["avatar"]
        declared_content_type = getattr(avatar, "content_type", None)
        if avatar.size > self.max_upload_size:
            raise ValidationError("La photo ne doit pas dépasser 2 Mo.")
        if declared_content_type not in self.allowed_content_types:
            raise ValidationError("Le format doit être JPEG, PNG ou WebP.")

        avatar.seek(0)
        content = avatar.read()
        avatar.seek(0)
        signature_format = self._format_from_signature(content[:12])
        if signature_format is None:
            raise ValidationError("La signature du fichier image est invalide.")
        if self.allowed_content_types[declared_content_type] != signature_format:
            raise ValidationError("Le type MIME déclaré ne correspond pas au contenu de l’image.")

        extension = avatar.name.rsplit(".", 1)[-1].lower()
        if extension not in self.extensions_by_format[signature_format]:
            raise ValidationError("L’extension ne correspond pas au contenu de l’image.")

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(
                    BytesIO(content), formats=self.allowed_pillow_formats
                ) as image:
                    detected_format = image.format
                    if detected_format not in self.canonical_content_types:
                        raise ValidationError("Le format doit être JPEG, PNG ou WebP.")
                    if detected_format != signature_format:
                        raise ValidationError("Le format détecté ne correspond pas au fichier.")

                    width, height = image.size
                    if (
                        width > self.max_dimension
                        or height > self.max_dimension
                        or width * height > self.max_pixels
                    ):
                        raise ValidationError(
                            "La photo ne doit pas dépasser 4096 × 4096 pixels."
                        )
                    image.verify()
        except ValidationError:
            raise
        except Exception as error:
            raise ValidationError("Le fichier image est invalide ou illisible.") from error

        avatar.content_type = self.canonical_content_types[detected_format]
        avatar.seek(0)
        return avatar
