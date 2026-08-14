# Configuration des environnements

## Objet

Ce document décrit la configuration effectivement utilisée par le MVP C-Tech Archives. Les valeurs réelles de production ne doivent jamais être ajoutées au dépôt : seule la structure non sensible de [`.env.example`](../.env.example) est versionnée. Le fichier `.env` local et les variables de déploiement restent hors Git.

## Profils d’environnement

| Environnement | `DJANGO_ENV` | `DJANGO_DEBUG` | Base de données | Règle principale |
|---|---|---:|---|---|
| Développement | `development` | `True` par défaut | PostgreSQL local | HTTP local autorisé ; hôtes locaux par défaut |
| Test | `test` ou environnement du runner | Selon le runner | Base PostgreSQL de test créée par Django | Données et fichiers synthétiques uniquement |
| Production | `production` | `False` obligatoire | PostgreSQL dédiée | HTTPS, cookies secure, HSTS et hôtes explicites |

## Variables d’environnement

| Variable | Obligatoire | Développement | Production | Exemple non sensible |
|---|---|---|---|---|
| `DJANGO_ENV` | Oui | `development` | `production` | `production` |
| `DJANGO_SECRET_KEY` | Oui | Secret local non versionné | Secret unique protégé et renouvelable | `replace-with-a-unique-long-random-secret` |
| `DJANGO_DEBUG` | Oui | `True` possible | `False` obligatoire | `False` |
| `DJANGO_ALLOWED_HOSTS` | Oui hors DEBUG | `localhost,127.0.0.1` par défaut | Liste explicite, sans `*` | `archives.example` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Selon les origines HTTPS | Vide si inutile | Origines HTTPS réelles | `https://archives.example` |
| `POSTGRES_DB` | Oui | Base locale | Base dédiée | `c_tech_archives` |
| `POSTGRES_USER` | Oui | Rôle applicatif local | Rôle applicatif à privilèges limités | `c_tech_app` |
| `POSTGRES_PASSWORD` | Oui | Secret local non versionné | Secret protégé hors Git | `replace-with-a-strong-database-password` |
| `POSTGRES_HOST` | Oui | `127.0.0.1` | Hôte ou service PostgreSQL privé | `127.0.0.1` |
| `POSTGRES_PORT` | Oui | `5432` | Port défini par l’infrastructure | `5432` |
| `POSTGRES_CONN_MAX_AGE` | Non | `60` | Valeur adaptée à l’infrastructure | `60` |
| `PRIVATE_MEDIA_ROOT` | Oui pour les fichiers | `private_media` | Répertoire ou montage privé | `/srv/c-tech/private_media` |
| `ARCHIVE_MAX_UPLOAD_SIZE` | Oui | `10485760` | Valeur validée avec C-Tech et proxy | `10485760` |
| `ARCHIVE_ALLOWED_EXTENSIONS` | Oui | Allowlist MVP | Liste métier validée | `.pdf,.doc,.docx,.xls,.xlsx,.txt,.jpg,.jpeg,.png` |
| `DJANGO_SESSION_COOKIE_SECURE` | Non localement | `False` possible | `True` | `True` |
| `DJANGO_CSRF_COOKIE_SECURE` | Non localement | `False` possible | `True` | `True` |
| `DJANGO_SECURE_SSL_REDIRECT` | Non localement | `False` possible | `True` ou équivalent proxy documenté | `True` |
| `DJANGO_SECURE_HSTS_SECONDS` | Non localement | `0` | Valeur positive après HTTPS complet | `31536000` |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | Non localement | `False` | Décision explicite après validation des sous-domaines | `True` |
| `DJANGO_SECURE_HSTS_PRELOAD` | Non localement | `False` | Décision explicite, après HTTPS complet | `False` |
| `DJANGO_USE_X_FORWARDED_PROTO` | Non | `False` | `True` seulement avec proxy de confiance documenté | `False` |

## Validation appliquée par Django

Le secret Django est requis au chargement des paramètres. Hors DEBUG, `DJANGO_ALLOWED_HOSTS` doit être renseigné et ne peut pas contenir `*`. Cette validation lève `ImproperlyConfigured` lorsqu’une configuration production est ambiguë. Elle ne restreint pas les hôtes de développement `localhost` et `127.0.0.1`.

Le contrôle `python manage.py check --deploy` produit cinq warnings attendus en développement HTTP/DEBUG : HSTS, redirection HTTPS, cookies secure et DEBUG. Ces warnings ne sont pas masqués. Un profil production simulé avec hôte explicite, HTTPS, cookies secure, redirection SSL, HSTS et preload activés ne produit aucun warning.

## PostgreSQL

Le MVP utilise `django.db.backends.postgresql`. Le compte applicatif doit être distinct d’un superutilisateur PostgreSQL, et la base de production doit être sauvegardée et protégée par les procédures de l’infrastructure C-Tech. Dans le sandbox local de test, le compte de développement peut nécessiter `CREATEDB` uniquement pour que Django crée et détruise sa base temporaire. Cette exception ne doit pas être transposée à la production.

## Stockage privé

Les documents ne sont pas conservés dans PostgreSQL et ne sont jamais publiés par `MEDIA_URL`. PostgreSQL conserve les métadonnées et le chemin relatif du `FileField`, tandis que le contenu est écrit dans `PRIVATE_MEDIA_ROOT`. Le serveur web ne doit pas mapper ce répertoire vers une URL publique. Le téléchargement passe par `/archives/<pk>/download/`, avec authentification et autorisation applicatives.

Les fichiers, comptes et référentiels de démonstration sont synthétiques. Aucun document réel C-Tech, identifiant personnel, mot de passe, clé Django ou artefact de production ne doit être ajouté au dépôt.

## Limites d’infrastructure

Le projet n’implémente pas de sauvegarde/restauration, gestion de secrets externe, antivirus, chiffrement applicatif au repos, monitoring centralisé, SIEM/WORM ou configuration de reverse proxy. Ces éléments restent des prérequis ou perspectives de production, à valider avec C-Tech.
