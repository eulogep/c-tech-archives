# Configuration PostgreSQL et environnements

## Objet

Ce document accompagne le ticket **T-002**. Il décrit la configuration nécessaire au démarrage de Django avec PostgreSQL et les réglages à renseigner avant tout déploiement. Les valeurs réelles de production ne doivent jamais être ajoutées au dépôt : le fichier versionné est uniquement [`.env.example`](../.env.example).

## Environnements

| Environnement | `DJANGO_ENV` | `DJANGO_DEBUG` | Base de données | Règle de sécurité |
|---|---|---:|---|---|
| Développement | `development` | `True` | PostgreSQL local | HSTS désactivé ; HTTPS non imposé localement |
| Test | `test` | `False` ou `True` selon le runner | Base de test PostgreSQL créée par Django | Aucune donnée réelle C-Tech |
| Production | `production` | `False` | Instance PostgreSQL dédiée ou administrée | HTTPS, cookies sécurisés et hôtes explicites obligatoires |

## Variables obligatoires

| Variable | Rôle | Exemple sans secret réel |
|---|---|---|
| `DJANGO_ENV` | Sélection de l’environnement | `production` |
| `DJANGO_SECRET_KEY` | Secret cryptographique Django | Valeur aléatoire longue, non versionnée |
| `DJANGO_DEBUG` | Mode de débogage | `False` en production |
| `DJANGO_ALLOWED_HOSTS` | Domaines acceptés par Django | `archives.exemple.c-tech.tld` |
| `POSTGRES_DB` | Nom de la base | `c_tech_archives` |
| `POSTGRES_USER` | Compte applicatif PostgreSQL | `c_tech_app` |
| `POSTGRES_PASSWORD` | Mot de passe du compte applicatif | Secret stocké hors Git |
| `POSTGRES_HOST` et `POSTGRES_PORT` | Adresse de la base | `127.0.0.1` et `5432` en local |

## Mise en place locale

Après installation de PostgreSQL, un rôle applicatif non superutilisateur et une base dédiée sont créés. Le compte applicatif est propriétaire de la base locale de développement, mais ne doit pas disposer de privilèges d’administration PostgreSQL. Un fichier `.env` local, ignoré par Git et lisible seulement par son propriétaire, contient la clé Django et le mot de passe de développement.

La connexion est vérifiée par la configuration Django et par l’exécution des migrations. Le projet utilise le backend `django.db.backends.postgresql`, avec des connexions persistantes contrôlées et une vérification d’état activée.

## Exigences avant production

| Contrôle | Valeur attendue | Justification |
|---|---|---|
| Clé Django | Valeur unique, longue et stockée dans un gestionnaire de secrets ou une variable protégée | Protège les mécanismes cryptographiques de Django |
| Débogage | `DJANGO_DEBUG=False` | Évite l’exposition de détails techniques dans les erreurs |
| Hôtes | `DJANGO_ALLOWED_HOSTS` non vide et limité aux domaines C-Tech | Réduit les requêtes Host non prévues |
| HTTPS | Certificat TLS valide et `DJANGO_SECURE_SSL_REDIRECT=True` | Protège les sessions et les échanges réseau |
| Cookies | `DJANGO_SESSION_COOKIE_SECURE=True` et `DJANGO_CSRF_COOKIE_SECURE=True` | Empêche l’envoi des cookies sur HTTP |
| HSTS | Activer après vérification HTTPS ; commencer sans préchargement | Évite d’imposer HTTPS de manière irréversible avant validation |
| Proxy | `DJANGO_USE_X_FORWARDED_PROTO=True` seulement pour un proxy de confiance documenté | Empêche la confiance abusive dans un en-tête HTTP forgé |
| PostgreSQL | Instance sauvegardée, accès réseau restreint et compte applicatif sans privilèges superutilisateur | Préserve confidentialité et disponibilité des données |

## Limites du ticket

T-002 prépare la configuration. Il n’implémente pas encore la politique de sauvegarde de production, le chiffrement au repos, le déploiement HTTPS, le modèle `User` personnalisé ou les modèles métier. Ces sujets restent dépendants des informations à valider avec C-Tech et des tickets ultérieurs.
