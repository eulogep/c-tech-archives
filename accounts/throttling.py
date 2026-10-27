"""Limitation des tentatives de connexion et d’inscription.

Les compteurs vivent dans le cache Django (table partagée en production). Les
clés sont des empreintes : aucun identifiant ni adresse IP n’y figure en clair.
"""

from __future__ import annotations

import math
import time
from hashlib import sha256

from django.conf import settings
from django.core.cache import cache


def _key(kind: str, value: str) -> str:
    digest = sha256(f"{kind}:{value}".encode()).hexdigest()
    return f"ctech:throttle:{kind}:{digest}"


def normalize_identifier(identifier: str | None) -> str:
    return (identifier or "").strip().lower()


def login_lockout_remaining(identifier: str) -> int:
    """Secondes restantes avant de pouvoir retenter, 0 si l’identifiant est libre."""
    if not identifier:
        return 0
    state = cache.get(_key("login", identifier))
    if not state:
        return 0
    remaining = state.get("locked_until", 0) - time.time()
    return max(0, math.ceil(remaining))


def register_login_failure(identifier: str) -> int:
    """Compte un échec et retourne la durée de verrouillage éventuellement déclenchée."""
    if not identifier:
        return 0
    key = _key("login", identifier)
    window = settings.AUTH_LOGIN_LOCKOUT_SECONDS
    state = cache.get(key) or {"failures": 0, "locked_until": 0}
    state["failures"] += 1
    locked_for = 0
    if state["failures"] >= settings.AUTH_LOGIN_FAILURE_LIMIT:
        state["locked_until"] = time.time() + window
        state["failures"] = 0
        locked_for = window
    cache.set(key, state, timeout=window)
    return locked_for


def reset_login_failures(identifier: str) -> None:
    if identifier:
        cache.delete(_key("login", identifier))


def signup_allowed(client_key: str) -> bool:
    """Indique si une nouvelle inscription est permise pour cette origine."""
    attempts = cache.get(_key("signup", client_key or "unknown"), 0)
    return attempts < settings.AUTH_SIGNUP_LIMIT


def register_signup(client_key: str) -> None:
    key = _key("signup", client_key or "unknown")
    window = settings.AUTH_SIGNUP_WINDOW_SECONDS
    if cache.add(key, 1, timeout=window):
        return
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window)


def format_wait(seconds: int) -> str:
    minutes = max(1, math.ceil(seconds / 60))
    return f"{minutes} minute{'s' if minutes > 1 else ''}"
