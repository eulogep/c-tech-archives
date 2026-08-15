# Guide de Déploiement sur Render — C-Tech Archives

Ce document décrit la procédure de déploiement en ligne de l'application **C-Tech Archives** sur la plateforme Render pour la démonstration de soutenance.

---

## 1. Caractéristiques du Déploiement

- **Plateforme :** Render (Web Service + Managed PostgreSQL).
- **Runtime :** Python 3.13.x.
- **Framework :** Django 5.1.x.
- **Serveur WSGI :** Gunicorn.
- **Fichiers statiques :** WhiteNoise (`CompressedManifestStaticFilesStorage`).
- **Stockage des documents privés :** `PRIVATE_FILE_STORAGE: EPHEMERAL` (système de fichiers local éphémère Render réservé à la démonstration en ligne).

---

## 2. Variables d'Environnement Requises

| Variable | Exemple / Valeur | Description |
|---|---|---|
| `DJANGO_ENV` | `production` | Active le profil de production Django |
| `DJANGO_DEBUG` | `False` | Désactive le mode debug |
| `DJANGO_SECRET_KEY` | *(clé aléatoire)* | Clé secrète cryptographique Django |
| `DJANGO_ALLOWED_HOSTS` | `c-tech-archives.onrender.com` | Hôte public Render assigné |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://c-tech-archives.onrender.com` | Origine HTTPS de confiance pour CSRF |
| `DJANGO_SESSION_COOKIE_SECURE` | `True` | Cookies de session sur HTTPS uniquement |
| `DJANGO_CSRF_COOKIE_SECURE` | `True` | Cookies CSRF sur HTTPS uniquement |
| `DJANGO_SECURE_SSL_REDIRECT` | `True` | Redirection automatique vers HTTPS |
| `DJANGO_USE_X_FORWARDED_PROTO` | `True` | Confiance dans l'en-tête HTTPS du proxy Render |
| `POSTGRES_DB` | `c_tech_archives` | Nom de la base PostgreSQL |
| `POSTGRES_USER` | `c_tech_app` | Utilisateur PostgreSQL |
| `POSTGRES_PASSWORD` | *(mot de passe)* | Mot de passe PostgreSQL |
| `POSTGRES_HOST` | `ctech-postgres-db` | Hôte interne PostgreSQL |
| `POSTGRES_PORT` | `5432` | Port PostgreSQL |
| `CTECH_STEVEN_EMAIL` | *(email Steven)* | Identifiant du compte Administrateur métier |
| `CTECH_STEVEN_PASSWORD` | *(mot de passe Steven)* | Mot de passe du compte Steven |
| `CTECH_EULOGE_EMAIL` | *(email Euloge)* | Identifiant du compte Administrateur technique |
| `CTECH_EULOGE_PASSWORD` | *(mot de passe Euloge)* | Mot de passe du compte Euloge |

---

## 3. Commandes de Build et d'Initialisation

### Build Command (Automatique lors du déploiement)
```bash
./build.sh
```

### Initialisation de la Base de Données (Via Render Shell ou Release Command)
1. Application des migrations :
```bash
python manage.py migrate --noinput
```
2. Bootstrap sécurisé des comptes privilégiés :
```bash
python manage.py bootstrap_default_admins
```

---

## 4. Limites de Stockage

> [!WARNING]
> Sur l'offre Render Web Service standard, le système de fichiers est éphémère. Les archives uploadées lors de la session de test peuvent disparaître lors d'un redémarrage de l'instance. Cette version constitue une **démonstration en ligne** avec données synthétiques.
