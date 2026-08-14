"""Stockage privé des documents d’archives, contrôlé par les vues Django."""

import os
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


def archive_private_upload_to(instance, filename: str) -> str:
    """Retourne un nom physique aléatoire, sans réutiliser le chemin client."""
    extension = Path(filename).suffix.lower()
    return f"archives/{uuid4().hex}{extension}"


@deconstructible
class PrivateArchiveStorage(FileSystemStorage):
    """Stockage local privé, reconfigurable via ``PRIVATE_MEDIA_ROOT``.

    L’absence d’URL de base interdit son emploi comme mécanisme de diffusion
    publique. Le chemin reste dynamique pour isoler les tests avec
    ``override_settings``.
    """

    def __init__(self):
        super().__init__(location=None, base_url=None)

    @property
    def base_location(self) -> str:
        return str(settings.PRIVATE_MEDIA_ROOT)

    @property
    def location(self) -> str:
        return os.path.abspath(self.base_location)

    @property
    def base_url(self):
        return None


private_archive_storage = PrivateArchiveStorage()
