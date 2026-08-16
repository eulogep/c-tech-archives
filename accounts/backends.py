"""Backends d’authentification adaptés à l’identifiant e-mail de C-Tech."""

from __future__ import annotations

from django.contrib.auth.backends import ModelBackend

from .models import User


class EmailBackend(ModelBackend):
    """Authentifie un utilisateur actif à partir de son e-mail, sans fuite d’existence."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email") or username
        if email is None or password is None:
            return None

        identifier = email.strip()
        user = User.objects.filter(email__iexact=identifier).first()
        # Transition MVP : les anciens comptes conservent un identifiant technique.
        if user is None:
            user = User.objects.filter(username__iexact=identifier).first()
        if user is None:
            # Conserve un coût de hachage comparable pour limiter l’énumération de comptes.
            User().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
