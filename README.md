# C-Tech Archives

> **Le coffre documentaire de C-Tech** — archives, intégrité SHA-256 et traçabilité, dans une interface pensée comme un sceau.

C-Tech Archives centralise les métadonnées et documents d’archives dans un monolithe Django modulaire. Les accès sont décidés côté serveur et refusés par défaut, les fichiers restent privés, chaque action sensible est journalisée et l’intégrité de chaque document peut être revérifiée à tout moment.

**Production :** [https://c-tech-archives.onrender.com](https://c-tech-archives.onrender.com) · sonde de santé : `/healthz/`

## Version 2.0 en bref

| Domaine | Ce qui change |
|---|---|
| Interface | Système de design « Sceau » : thèmes clair, sombre et système ; typographies Fraunces, Geist et Geist Mono auto-hébergées ; sceau génératif unique par archive ; tableau de bord analytique ; responsive jusqu’à 360 px |
| Productivité | Palette de commandes <kbd>Ctrl</kbd>/<kbd>⌘</kbd> <kbd>K</kbd> avec recherche d’archives en direct filtrée par le RBAC ; raccourcis clavier (<kbd>/</kbd>, <kbd>G</kbd> <kbd>A</kbd>, <kbd>N</kbd>, <kbd>T</kbd>, <kbd>?</kbd>) ; vue tableau ou grille ; tri ; filtres actifs retirables |
| Archives | Glisser-déposer avec contrôle anticipé ; aperçu à la demande des images et textes (tracé dans l’audit) ; panneau d’intégrité visuel ; historique des accès pour les administrateurs ; fiche imprimable |
| Audit | Chronologie groupée par jour, filtres par période, export CSV protégé contre l’injection de formules (l’export est lui-même audité) |
| Comptes | Changement de mot de passe en libre-service (audité), retrait de l’avatar, carte d’habilitation, verrouillage temporaire après échecs de connexion, limitation des inscriptions |
| Sécurité | Content-Security-Policy stricte sans `unsafe-inline`, Permissions-Policy, session de 8 h, Django 5.2 LTS, Pillow 13, **0 vulnérabilité connue** (`pip-audit`) |
| Exploitation | Journaux console (les erreurs 500 sont enfin visibles), `/healthz/`, statiques hachés et compressés, cache partagé, CI GitHub Actions, versions figées (`constraints.txt`), `docker compose`, `Makefile`, `seed_demo` |

Le détail figure dans [`CHANGELOG.md`](CHANGELOG.md) et la charte graphique dans [`docs/design-system.md`](docs/design-system.md).

## Stack

| Couche | Technologie |
|---|---|
| Framework | Django 5.2 LTS (support jusqu’en avril 2028) |
| Base de données | PostgreSQL 17 via `psycopg` 3.2 |
| Fichiers statiques | WhiteNoise, manifeste haché et gzip en production |
| Images | Pillow 13 (avatars, validation) |
| Serveur | gunicorn |
| Interface | Django Templates, CSS et JavaScript sans dépendance, sprite SVG interne |
| Tests | Django TestCase : **362 tests** en ~13 s |

Aucun CDN, aucune police ni aucun script tiers : tout est servi par l’application, ce qui permet la CSP stricte.

## Démarrage rapide

```bash
git clone https://github.com/eulogep/c-tech-archives.git
cd c-tech-archives
cp .env.example .env            # puis renseigner les secrets locaux
make setup                       # venv + versions figées
make db                          # PostgreSQL local (docker compose)
make migrate
CTECH_DEMO_PASSWORD='un-mot-de-passe-robuste' make seed   # données de démonstration
make run                         # http://127.0.0.1:8000
```

Sans `make` : `python -m venv .venv`, `pip install -r requirements.txt -c constraints.txt`, `python manage.py migrate`, `python manage.py runserver`.

`seed_demo` crée trois comptes (`demo.admin@ctech.test`, `demo.agent@ctech.test`, `demo.consultant@ctech.test`), 42 archives réalistes et dix-huit semaines d’audit. La commande est idempotente, refusée en production et n’affiche jamais le mot de passe. L’archive `CT-DEMO-0013` a un fichier volontairement altéré : sa vérification d’intégrité déclenche une alerte, utile en démonstration.

Les comptes privilégiés réels sont créés par `python manage.py bootstrap_default_admins` à partir des variables `CTECH_*` (voir plus bas). **Ne commitez jamais `.env`, des mots de passe ou des données réelles C-Tech.**

## Rôles et habilitations

| Rôle | Niveaux visibles | Actions principales |
|---|---|---|
| Consultant | Public | Consulter, rechercher, prévisualiser, télécharger, vérifier l’intégrité |
| Agent d’archives | Public, Interne | + créer et modifier dans son périmètre |
| Administrateur | Public, Interne, Confidentiel | + journal d’audit, export CSV, historique des accès |
| Superutilisateur technique | Tous | Administration Django (référentiels, comptes) |

Une archive hors périmètre répond 404 (anti-inférence). Les compteurs, graphiques, la palette et la recherche instantanée sont calculés sur le seul périmètre visible. La matrice complète est dans [`docs/final-rbac-matrix.md`](docs/final-rbac-matrix.md).

## Configuration

| Variable | Rôle | Exemple non sensible |
|---|---|---|
| `DJANGO_SECRET_KEY` | Secret Django obligatoire | `replace-with-a-unique-long-random-secret` |
| `DJANGO_ENV` | Profil | `development` ou `production` |
| `DJANGO_DEBUG` | Debug | `True` en local, `False` en production |
| `DJANGO_ALLOWED_HOSTS` | Hôtes acceptés (`*` refusé hors debug) | `localhost,127.0.0.1` |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Base et rôle applicatif | `c_tech_archives` / `c_tech_app` / secret local |
| `POSTGRES_HOST` / `POSTGRES_PORT` | Connexion | `127.0.0.1` / `5432` |
| `PRIVATE_MEDIA_ROOT` | Documents privés | `private_media` |
| `ARCHIVE_MAX_UPLOAD_SIZE` / `ARCHIVE_ALLOWED_EXTENSIONS` | Limites d’upload | `10485760` / `.pdf,.docx,…` |
| `CTECH_STEVEN_EMAIL` / `CTECH_STEVEN_PASSWORD` | Administrateur métier | `business-administrator@example.invalid` |
| `CTECH_EULOGE_EMAIL` / `CTECH_EULOGE_PASSWORD` | Superutilisateur technique | `technical-administrator@example.invalid` |
| `CTECH_BOOTSTRAP_RECONCILE` | Réaligner les comptes privilégiés au prochain démarrage | `False` |
| `CTECH_LOGIN_FAILURE_LIMIT` / `CTECH_LOGIN_LOCKOUT_SECONDS` | Verrouillage après échecs | `5` / `900` |
| `CTECH_SIGNUP_LIMIT` / `CTECH_SIGNUP_WINDOW_SECONDS` | Inscriptions par origine | `10` / `3600` |
| `DJANGO_SESSION_COOKIE_AGE` | Durée de session | `28800` (8 h) |
| `DJANGO_LOG_LEVEL` | Niveau des journaux applicatifs | `INFO` |
| `DJANGO_CACHE_BACKEND` | Cache des compteurs | `database` (production) ou `locmem` |

Les mots de passe des comptes privilégiés doivent respecter les validateurs Django : un mot de passe faible est refusé par la commande de bootstrap.

## Vérifications

```bash
make check          # manage.py check + dérive des migrations
make test           # 362 tests
make audit-deps     # pip-audit sur constraints.txt
python manage.py check --deploy   # à lancer avec le profil de production
```

La CI GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) exécute ces contrôles sur Python 3.12 et 3.13 avec PostgreSQL 17, construit les statiques de production et lance `pip-audit`.

## Déploiement

Le blueprint [`render.yaml`](render.yaml) décrit le service web et la base. Au démarrage : migrations, table de cache, création des comptes privilégiés manquants (sans jamais réactiver ni réinitialiser un compte existant), puis gunicorn. Render surveille `/healthz/`. La procédure et les limites de l’offre gratuite sont dans [`docs/deployment-render.md`](docs/deployment-render.md).

## Structure

```text
accounts/       identité, rôles, connexion limitée, profil, feuille de route
archives/       domaine documentaire, RBAC, fichiers, intégrité, sceaux, aperçus
audit/          journal métier, chronologie, export CSV
dashboard/      indicateurs et graphiques du périmètre visible
config/         paramètres, CSP, santé, contexte d’interface
templates/      gabarits (partials : icônes, avatar, pagination, guide)
static/         css/app.css, js/app.js, polices OFL, favicon, manifeste
tests/          tests transverses, sécurité, interface et v2
docs/           documentation technique, académique et de démonstration
```

## Limites connues

Pas de MFA, d’antivirus, de chiffrement applicatif au repos, de signature électronique ni de versioning documentaire. Sur l’offre gratuite de Render, le disque est éphémère : les fichiers déposés disparaissent au redémarrage, et la base gratuite expire. La limitation des connexions est par compte (une adresse IP derrière le proxy Render est partagée) ; celle des inscriptions porte sur l’adresse vue par l’application. Le projet ne doit pas être présenté comme « totalement sécurisé » : la revue et les risques résiduels sont dans [`docs/security-review.md`](docs/security-review.md).

## Documentation

| Document | Contenu |
|---|---|
| [`CHANGELOG.md`](CHANGELOG.md) | Historique des versions |
| [`docs/design-system.md`](docs/design-system.md) | Charte « Sceau » : jetons, composants, accessibilité, CSP |
| [`docs/deployment-render.md`](docs/deployment-render.md) | Déploiement Render et diagnostic |
| [`docs/installation.md`](docs/installation.md) | Installation détaillée Linux, macOS et Windows |
| [`docs/architecture-final.md`](docs/architecture-final.md) | Architecture et modèle de données |
| [`docs/final-rbac-matrix.md`](docs/final-rbac-matrix.md) | Matrice par rôle et confidentialité |
| [`docs/security-review.md`](docs/security-review.md) | Revue sécurité et risques résiduels |
| [`docs/tests.md`](docs/tests.md) | Stratégie et matrice de tests |
| [`docs/demo-script.md`](docs/demo-script.md) | Scripts de démonstration |
| [`docs/jury-questions.md`](docs/jury-questions.md) | Questions et réponses de jury |

## Licence

Code : modalités à définir avec C-Tech et l’établissement académique. Polices Fraunces et Geist : SIL Open Font License 1.1 (licences dans `static/fonts/`).
