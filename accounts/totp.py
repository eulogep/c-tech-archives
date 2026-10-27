"""Mots de passe à usage unique basés sur le temps (TOTP, RFC 6238).

Implémentation volontairement courte, sans dépendance : HMAC-SHA1, 6 chiffres,
période de 30 s, compatible avec les applications d’authentification usuelles.
Le compteur accepté est mémorisé par l’appelant pour refuser le rejeu d’un
code déjà utilisé.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote, urlencode

from django.utils.crypto import salted_hmac


DIGITS = 6
PERIOD = 30
ISSUER = "C-Tech Archives"
RECOVERY_CODE_COUNT = 8
_RECOVERY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def generate_secret() -> str:
    """Secret de 160 bits encodé en base32, sans remplissage."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _key(secret: str) -> bytes:
    padding = "=" * (-len(secret) % 8)
    return base64.b32decode(secret.upper() + padding)


def code_at(secret: str, counter: int) -> str:
    digest = hmac.new(_key(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{value % 10**DIGITS:0{DIGITS}d}"


def current_counter(now: float | None = None) -> int:
    return int((time.time() if now is None else now) // PERIOD)


def verify(secret: str, code: str, *, last_counter: int | None = None, window: int = 1, now=None):
    """Retourne le compteur correspondant au code, ou None.

    Une dérive d’horloge d’une période est tolérée de part et d’autre ; un
    compteur inférieur ou égal au dernier accepté est refusé (anti-rejeu).
    """
    digits = "".join(character for character in str(code or "") if character.isdigit())
    if not secret or len(digits) != DIGITS:
        return None
    counter = current_counter(now)
    for candidate in range(counter - window, counter + window + 1):
        if last_counter is not None and candidate <= last_counter:
            continue
        if hmac.compare_digest(code_at(secret, candidate), digits):
            return candidate
    return None


def provisioning_uri(secret: str, account: str) -> str:
    """URI otpauth:// à présenter sous forme de QR code."""
    label = quote(f"{ISSUER}:{account}")
    query = urlencode(
        {"secret": secret, "issuer": ISSUER, "algorithm": "SHA1", "digits": DIGITS, "period": PERIOD}
    )
    return f"otpauth://totp/{label}?{query}"


def format_secret(secret: str) -> str:
    """Secret lisible par groupes de quatre, pour une saisie manuelle."""
    return " ".join(secret[index : index + 4] for index in range(0, len(secret), 4))


def generate_recovery_codes(count: int = RECOVERY_CODE_COUNT) -> list[str]:
    """Codes de secours à forte entropie (≈ 49 bits), au format xxxxx-xxxxx."""
    codes = []
    for _ in range(count):
        raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(10))
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes


def hash_recovery_code(code: str) -> str:
    """Empreinte HMAC liée à SECRET_KEY ; suffisante pour des codes aléatoires."""
    normalized = "".join(character for character in code.lower() if character.isalnum())
    return salted_hmac("ctech.recovery-code", normalized, algorithm="sha256").hexdigest()
