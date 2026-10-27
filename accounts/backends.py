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

    def get_user(self, user_id):
        """Charge l’utilisateur de session sans les octets de son avatar.

        AuthenticationMiddleware appelle cette méthode à chaque requête : un
        avatar de 2 Mo multipliait par 3,3 le temps de rendu des pages.
        """
        try:
            user = User._default_manager.defer("profile_avatar").get(pk=user_id)
        except User.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
