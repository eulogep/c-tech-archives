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

## Particularité du compte local de test

Le compte `c_tech_app` de cet environnement de développement possède le privilège PostgreSQL `CREATEDB`, uniquement pour permettre à `python manage.py test` de créer puis détruire sa base temporaire `test_c_tech_archives`. Il reste non superutilisateur et ne dispose ni de `CREATEROLE` ni de privilèges d’administration du serveur.

Ce compromis est spécifique au sandbox de développement. En production, le compte exécutant l’application ne doit pas recevoir `CREATEDB`. Les migrations et les opérations d’administration de base doivent y être exécutées par un compte de déploiement distinct, soumis aux procédures C-Tech de sauvegarde et de changement.


## Stockage privé des archives — T-010

Les documents d’archives ne sont pas stockés dans PostgreSQL et ne sont pas diffusés par `MEDIA_URL`. Le contenu est écrit par Django Storage dans un répertoire privé configuré, tandis que PostgreSQL conserve uniquement le chemin relatif du `FileField` et les métadonnées associées.

| Variable | Valeur de développement | Rôle | Exigence de production |
|---|---|---|---|
| `PRIVATE_MEDIA_ROOT` | `private_media` résolu sous la racine du projet | Répertoire de contenu privé des archives | Chemin absolu ou montage privé, accessible au processus applicatif mais non publié par le serveur web |
| `ARCHIVE_MAX_UPLOAD_SIZE` | `10485760` (10 MiB) | Plafond applicatif de taille en octets | Valeur à confirmer avec C-Tech et cohérente avec les limites du proxy/web server |
| `ARCHIVE_ALLOWED_EXTENSIONS` | `.pdf,.doc,.docx,.xls,.xlsx,.txt,.jpg,.jpeg,.png` | Allowlist provisoire de formats documentaires | Liste métier validée par C-Tech, revue à chaque extension ajoutée |

`private_media/` est ignoré par Git. Aucun fichier C-Tech, document réel, image personnelle ou artefact de test ne doit être ajouté au dépôt. Les tests redéfinissent `PRIVATE_MEDIA_ROOT` avec un répertoire temporaire, supprimé après leur exécution.

En production, le serveur web ne doit pas mapper le répertoire privé vers une URL. Le téléchargement doit rester routé par `/archives/<pk>/download/`, où Django applique l’authentification et la garde temporaire `StaffRequiredMixin` avant de retourner une réponse en pièce jointe. Le backend local est adapté au MVP ; il pourra être remplacé par un stockage objet privé ou réseau sans changer le modèle métier qui dépend de l’abstraction Django Storage.
