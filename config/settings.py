"""Paramètres Django de la plateforme de gestion des archives C-Tech.

Les secrets et paramètres d'infrastructure sont lus depuis l'environnement.
Le fichier local .env est réservé au développement et n'est jamais versionné.
"""

import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    """Interprète une variable booléenne d'environnement de manière explicite."""
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    """Retourne une liste séparée par des virgules sans éléments vides."""
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


def required_env(name: str) -> str:
    """Retourne une variable obligatoire ou interrompt le démarrage de manière sûre."""
    value = os.getenv(name)
    if not value:
        raise ImproperlyConfigured(f"La variable d'environnement {name} doit être définie.")
    return value


def env_int(name: str, default: int) -> int:
    """Retourne un entier d'environnement avec un message de configuration explicite."""
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as error:
        raise ImproperlyConfigured(f"La variable d'environnement {name} doit être un entier.") from error


APP_VERSION = "2.0.0"
RUNNING_TESTS = len(sys.argv) > 1 and sys.argv[1] == "test"

DJANGO_ENV = os.getenv("DJANGO_ENV", "development").strip().lower()
if DJANGO_ENV not in {"development", "test", "production"}:
    raise ImproperlyConfigured("DJANGO_ENV doit valoir development, test ou production.")

DEBUG = env_bool("DJANGO_DEBUG", default=DJANGO_ENV != "production")
if DJANGO_ENV == "production" and DEBUG:
    raise ImproperlyConfigured("DJANGO_DEBUG doit être désactivé en production.")

SECRET_KEY = required_env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    default="localhost,127.0.0.1" if DEBUG else "",
)
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS doit être défini hors développement.")
if not DEBUG and "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS ne doit pas contenir '*' hors développement."
    )

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "accounts",
    "archives",
    "audit",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "archives.context_processors.archive_policy",
                "audit.context_processors.audit_policy",
                "config.context_processors.interface",
            ],
            "builtins": [
                "archives.templatetags.archive_ui",
                "django.contrib.humanize.templatetags.humanize",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# PostgreSQL est requis dans tous les environnements du projet à partir de T-002.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": required_env("POSTGRES_DB"),
        "USER": required_env("POSTGRES_USER"),
        "PASSWORD": required_env("POSTGRES_PASSWORD"),
        "HOST": required_env("POSTGRES_HOST"),
        "PORT": required_env("POSTGRES_PORT"),
        "CONN_MAX_AGE": env_int("POSTGRES_CONN_MAX_AGE", 60),
        "CONN_HEALTH_CHECKS": True,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# Depuis Django 5.1, seul STORAGES est lu : l’ancien STATICFILES_STORAGE était
# ignoré silencieusement. Le manifeste haché n’existe qu’après collectstatic,
# il est donc réservé à la production.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if DJANGO_ENV == "production"
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        )
    },
}
WHITENOISE_MAX_AGE = 31536000 if DJANGO_ENV == "production" else 0


MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Les documents d’archives sont stockés hors de toute exposition MEDIA_URL.
PRIVATE_MEDIA_ROOT = Path(
    os.getenv("PRIVATE_MEDIA_ROOT", "private_media")
).expanduser()
if not PRIVATE_MEDIA_ROOT.is_absolute():
    PRIVATE_MEDIA_ROOT = BASE_DIR / PRIVATE_MEDIA_ROOT
ARCHIVE_MAX_UPLOAD_SIZE = env_int("ARCHIVE_MAX_UPLOAD_SIZE", 10 * 1024 * 1024)
ARCHIVE_ALLOWED_EXTENSIONS = env_list(
    "ARCHIVE_ALLOWED_EXTENSIONS",
    default=".pdf,.doc,.docx,.xls,.xlsx,.txt,.jpg,.jpeg,.png",
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

# Les empreintes de mots de passe coûteuses n’apportent rien aux tests et
# représentaient 90 % de leur durée ; la production garde le hasher par défaut.
if RUNNING_TESTS:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Authentification par session Django du MVP.
AUTHENTICATION_BACKENDS = ["accounts.backends.EmailBackend"]
LOGIN_URL = "/accounts/login/"
SESSION_COOKIE_AGE = env_int("DJANGO_SESSION_COOKIE_AGE", 8 * 60 * 60)

# Limitation des tentatives : par identifiant pour la connexion (une IP derrière
# le proxy Render est partagée), par adresse pour l’inscription.
AUTH_LOGIN_FAILURE_LIMIT = env_int("CTECH_LOGIN_FAILURE_LIMIT", 5)
AUTH_LOGIN_LOCKOUT_SECONDS = env_int("CTECH_LOGIN_LOCKOUT_SECONDS", 15 * 60)
AUTH_SIGNUP_LIMIT = env_int("CTECH_SIGNUP_LIMIT", 10)
AUTH_SIGNUP_WINDOW_SECONDS = env_int("CTECH_SIGNUP_WINDOW_SECONDS", 60 * 60)
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Cookies, navigateur et HTTPS : les valeurs de production doivent être explicites.
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE", default=not DEBUG)
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", default=not DEBUG)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SECURE_REDIRECT_EXEMPT = [r"^healthz/?$"]
X_FRAME_OPTIONS = "DENY"

# HSTS ne doit être activé qu'une fois HTTPS opérationnel sur le domaine final.
SECURE_HSTS_SECONDS = env_int("DJANGO_SECURE_HSTS_SECONDS", 0 if DEBUG else 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=not DEBUG
)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", default=False)

# Ne faire confiance au proxy HTTPS que si l'infrastructure le documente explicitement.
if env_bool("DJANGO_USE_X_FORWARDED_PROTO", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Le cache porte la limitation des tentatives : en production il doit être
# partagé entre les workers gunicorn, d’où la table créée par createcachetable.
CACHE_BACKEND = os.getenv(
    "DJANGO_CACHE_BACKEND", "database" if DJANGO_ENV == "production" else "locmem"
).strip().lower()
if CACHE_BACKEND not in {"database", "locmem"}:
    raise ImproperlyConfigured("DJANGO_CACHE_BACKEND doit valoir database ou locmem.")
CACHES = {
    "default": (
        {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "ctech_cache",
        }
        if CACHE_BACKEND == "database"
        else {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "ctech-local",
        }
    )
}

# Sans LOGGING, Django n’écrit rien sur la console quand DEBUG est faux : une
# erreur 500 en production ne laissait aucune trace dans les journaux Render.
LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO").strip().upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "CRITICAL" if RUNNING_TESTS else "ERROR",
            "propagate": False,
        },
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "ctech": {
            "handlers": ["console"],
            "level": "CRITICAL" if RUNNING_TESTS else LOG_LEVEL,
            "propagate": False,
        },
    },
}
