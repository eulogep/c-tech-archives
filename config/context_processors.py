"""Contexte d’interface commun : palette de commandes et habilitation visible.

Tout ce qui est listé ici est déjà filtré par rôle côté serveur : une entrée
absente de la palette n’est jamais simplement masquée par le navigateur.
"""

from django.conf import settings
from django.urls import reverse

from archives.models import ConfidentialityLevel
from archives.permissions import (
    can_create_archive,
    has_archive_access,
    visible_confidentiality_levels_for,
)
from audit.context_processors import audit_policy


LEVEL_AUDIENCES = {
    ConfidentialityLevel.PUBLIC: "Tous les rôles métier",
    ConfidentialityLevel.INTERNAL: "Agents d’archives et administrateurs",
    ConfidentialityLevel.CONFIDENTIAL: "Administrateurs uniquement",
}


def _command(label, *, group, icon, url=None, action=None, keywords="", shortcut=""):
    return {
        "label": label,
        "group": group,
        "icon": icon,
        "url": url,
        "action": action,
        "keywords": keywords,
        "shortcut": shortcut,
    }


def _commands_for(request):
    user = request.user
    commands = [
        _command(
            "Tableau de bord",
            group="Navigation",
            icon="grid",
            url=reverse("home"),
            keywords="accueil synthèse",
            shortcut="G D",
        )
    ]
    if has_archive_access(user):
        commands.append(
            _command(
                "Archives",
                group="Navigation",
                icon="archive",
                url=reverse("archives:list"),
                keywords="documents recherche liste",
                shortcut="G A",
            )
        )
    commands.append(
        _command(
            "Rapport d’activité",
            group="Navigation",
            icon="chart",
            url=reverse("report"),
            keywords="rapport statistiques imprimer pdf période",
            shortcut="G R",
        )
    )
    if can_create_archive(user):
        commands.append(
            _command(
                "Nouvelle archive",
                group="Actions",
                icon="plus",
                url=reverse("archives:create"),
                keywords="créer déposer ajouter",
                shortcut="N",
            )
        )
    if audit_policy(request)["audit_policy"]["can_view"]:
        commands.append(
            _command(
                "Journal d’audit",
                group="Navigation",
                icon="shield",
                url=reverse("audit:list"),
                keywords="traces événements sécurité",
                shortcut="G J",
            )
        )
        commands.append(
            _command(
                "Revue des droits",
                group="Navigation",
                icon="user",
                url=reverse("access_review"),
                keywords="comptes rôles habilitations double authentification inactifs",
            )
        )
    commands += [
        _command(
            "Futures améliorations",
            group="Navigation",
            icon="sparkles",
            url=reverse("future_improvements"),
            keywords="feuille de route votes",
        ),
        _command(
            "Mon profil",
            group="Compte",
            icon="user",
            url=reverse("profile"),
            keywords="photo avatar compte",
            shortcut="G P",
        ),
        _command(
            "Double authentification",
            group="Compte",
            icon="shield",
            url=reverse("two_factor"),
            keywords="2fa totp mfa sécurité code application",
        ),
        _command(
            "Changer mon mot de passe",
            group="Compte",
            icon="key",
            url=reverse("password_change"),
            keywords="sécurité identifiants",
        ),
        _command(
            "Basculer le thème clair / sombre",
            group="Préférences",
            icon="contrast",
            action="toggle-theme",
            keywords="mode nuit sombre clair apparence",
            shortcut="T",
        ),
        _command(
            "Lancer le guide d’utilisation",
            group="Préférences",
            icon="compass",
            action="open-guide",
            keywords="aide tutoriel découverte",
        ),
        _command(
            "Raccourcis clavier",
            group="Préférences",
            icon="keyboard",
            action="open-shortcuts",
            keywords="clavier aide",
            shortcut="?",
        ),
        _command(
            "Se déconnecter",
            group="Compte",
            icon="logout",
            action="logout",
            keywords="quitter fermer session",
        ),
    ]
    return commands


def interface(request):
    """Expose la version, l’habilitation du compte et les commandes autorisées."""
    context = {"app_version": settings.APP_VERSION}
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return context

    granted = visible_confidentiality_levels_for(user)
    context["clearance_levels"] = [
        {
            "value": value,
            "label": label,
            "granted": value in granted,
            "audience": LEVEL_AUDIENCES[value],
        }
        for value, label in ConfidentialityLevel.choices
    ]
    context["clearance_granted_count"] = len(granted)
    context["command_items"] = _commands_for(request)
    context["can_search_archives"] = has_archive_access(user)
    return context
