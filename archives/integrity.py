"""Calcul et vérification centralisés de l’intégrité des fichiers d’archives."""

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256


CHUNK_SIZE = 64 * 1024


class IntegrityStatus(StrEnum):
    """États non ambigus retournés lors d’une vérification d’intégrité."""

    VALID = "VALID"
    MISMATCH = "MISMATCH"
    NO_FILE = "NO_FILE"
    MISSING_CHECKSUM = "MISSING_CHECKSUM"
    FILE_MISSING = "FILE_MISSING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class IntegrityResult:
    """Résultat de vérification sans révéler l’empreinte dans l’interface."""

    status: IntegrityStatus


def calculate_sha256(file_obj) -> str:
    """Calcule l’empreinte SHA-256 du flux entier par blocs de 64 KiB.

    Lorsque le flux est repositionnable, le calcul commence au début puis restaure
    la position initiale afin de ne pas perturber le stockage ou le téléchargement.
    """
    original_position = None
    try:
        original_position = file_obj.tell()
        file_obj.seek(0)
    except (AttributeError, OSError):
        original_position = None

    hasher = sha256()
    try:
        while chunk := file_obj.read(CHUNK_SIZE):
            hasher.update(chunk)
    finally:
        if original_position is not None:
            file_obj.seek(original_position)
    return hasher.hexdigest()


def calculate_archive_checksum(archive) -> str:
    """Calcule l’empreinte du fichier actuellement stocké pour une archive."""
    with archive.file.open("rb") as file_obj:
        return calculate_sha256(file_obj)


def verify_archive_integrity(archive) -> IntegrityResult:
    """Compare le contenu stocké à l’empreinte historique sans la modifier."""
    if not archive.file:
        return IntegrityResult(IntegrityStatus.NO_FILE)
    if not archive.checksum:
        return IntegrityResult(IntegrityStatus.MISSING_CHECKSUM)
    if not archive.file.storage.exists(archive.file.name):
        return IntegrityResult(IntegrityStatus.FILE_MISSING)

    try:
        calculated_checksum = calculate_archive_checksum(archive)
    except OSError:
        return IntegrityResult(IntegrityStatus.ERROR)

    if calculated_checksum == archive.checksum:
        return IntegrityResult(IntegrityStatus.VALID)
    return IntegrityResult(IntegrityStatus.MISMATCH)
