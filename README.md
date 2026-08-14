# C-Tech Archives

> **Plateforme sécurisée de gestion documentaire** — projet académique de Génie Informatique.

C-Tech Archives centralise les métadonnées et documents d’archives dans un MVP Django modulaire. Le projet privilégie une gestion documentaire explicable et vérifiable : les accès sont contrôlés côté serveur, les fichiers sont privés, les actions sensibles sont journalisées et l’intégrité du contenu peut être vérifiée par SHA-256.

## État du MVP

| Élément | État vérifiable |
|---|---|
| Socle applicatif | Django 5.1.x, PostgreSQL, Django Templates et CSS local responsive |
| Tests automatisés | **263 tests** avec `python manage.py test` |
| Rôles métier | Administrateur, Agent d’archives, Consultant |
| Niveaux de confidentialité | PUBLIC, INTERNAL, CONFIDENTIAL |
| Stockage documentaire | Privé, hors `MEDIA_URL`, téléchargement contrôlé |
| Audit | Journal métier append-only applicatif, lecture réservée à l’Administrateur/superuser |
| Intégrité | SHA-256 calculé après stockage et vérifié sur demande POST |
| Sécurité | Revue transverse T-014, profil de déploiement simulé et interface T-015 responsive |
| T-001 à T-016 | **INTEGRATED** dans `develop` ; T-005 reste `ABSORBED_BY_T004` |
| MVP académique | **FINALIZED** : MVP fonctionnel, 263 tests automatisés, revue de sécurité terminée, livraison académique achevée et limites de production documentées |

## Objectif

Le MVP permet à des utilisateurs authentifiés de consulter, rechercher, créer ou modifier des archives selon leur rôle et la confidentialité du document. Il ne prétend pas couvrir une gestion documentaire réglementaire complète ni remplacer une infrastructure de production spécialisée.

## Stack technique

| Couche | Technologie réellement utilisée |
|---|---|
| Framework web | Django 5.1.x |
| Base de données | PostgreSQL, via `psycopg[binary]` |
| Configuration | `python-dotenv` et variables d’environnement |
| Images de validation de fichiers | Pillow |
| Présentation | Django Templates et `static/css/app.css` |
| Tests | Django TestCase, Client de test et fichiers synthétiques |

Aucun framework frontend séparé, CDN critique, API REST, Docker, S3 ou architecture microservices n’est requis par le dépôt actuel.

## Fonctionnalités intégrées

| Capacité | Description courte |
|---|---|
| Authentification | Connexion par session Django, compte inactif refusé, redirection locale contrôlée et logout POST/CSRF |
| Rôles et RBAC | Politique centralisée de visibilité et d’actions par rôle, avec deny-by-default |
| Dashboard | Six métriques limitées au périmètre visible de l’utilisateur |
| Archives | Création et modification des métadonnées autorisées, sans suppression physique |
| Recherche | Recherche GET, filtres combinables et pagination avec query string conservée |
| Fichiers | Upload validé, stockage privé UUID et téléchargement par vue protégée |
| Confidentialité | PUBLIC, INTERNAL et CONFIDENTIAL appliqués avant liste, recherche, pagination et détail |
| Audit | Événements métier minimaux après opérations réussies ; interface Administrateur uniquement |
| Intégrité | Empreinte SHA-256 de référence et vérification explicite POST |
| Interface | Sidebar guidée par le rôle, tables responsive, formulaires structurés et états vides |

La matrice détaillée des fonctionnalités et preuves est disponible dans [`docs/final-feature-matrix.md`](docs/final-feature-matrix.md).

## Architecture

Le navigateur appelle les routes Django. Les vues appliquent l’authentification, le RBAC, les formulaires et les services, puis accèdent à PostgreSQL via l’ORM. Les fichiers sont conservés dans un stockage privé et ne sont renvoyés qu’après un contrôle d’accès ; l’audit et l’intégrité sont des services applicatifs séparés.

```text
Navigateur → URLs Django → Vues → Authentification / autorisation
                                 → Formulaires / services → ORM → PostgreSQL
                                 → Stockage privé
                                 → AuditLog
                                 → Service SHA-256
```

La description complète et le modèle de données sont dans [`docs/architecture-final.md`](docs/architecture-final.md).

## Sécurité

Les contrôles principaux sont l’authentification par session, CSRF, RBAC avec QuerySets filtrés, réponse 404 anti-inférence, formulaires à liste blanche, stockage privé, validation de fichiers, audit applicatif minimal et vérification SHA-256. En production, `DEBUG` doit être désactivé, les hôtes doivent être explicites et le wildcard `DJANGO_ALLOWED_HOSTS=*` est refusé.

> Le projet ne doit pas être présenté comme « totalement sécurisé ». Il ne fournit pas de MFA, rate limiting intégré, antivirus, chiffrement applicatif au repos, signature numérique, SIEM/WORM, pentest externe ni certification OWASP.

La revue, le modèle de menace et les risques résiduels sont documentés dans [`docs/security-review.md`](docs/security-review.md).

## Installation locale

Depuis un clone propre, créez un environnement virtuel, installez les dépendances, copiez `.env.example`, configurez PostgreSQL puis appliquez les migrations :

```bash
git clone https://github.com/eulogep/c-tech-archives.git
cd c-tech-archives
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Le guide détaillé Linux/macOS/Windows, les données synthétiques et les contrôles de configuration sont dans [`docs/installation.md`](docs/installation.md). **Ne commitez jamais `.env`, des mots de passe ou des données réelles C-Tech.**

## Configuration

Les variables sont chargées depuis `.env` en développement et depuis l’environnement en production.

| Variable | Rôle | Exemple non sensible |
|---|---|---|
| `DJANGO_SECRET_KEY` | Secret Django obligatoire | `replace-with-a-unique-long-random-secret` |
| `DJANGO_ENV` | Profil d’environnement | `development` ou `production` |
| `DJANGO_DEBUG` | Debug Django | `True` local, `False` en production |
| `DJANGO_ALLOWED_HOSTS` | Hôtes acceptés | `localhost,127.0.0.1` ou `archives.example` |
| `POSTGRES_DB` / `POSTGRES_USER` | Base et rôle applicatif | `c_tech_archives` / `c_tech_app` |
| `POSTGRES_PASSWORD` | Secret PostgreSQL | valeur locale non versionnée |
| `POSTGRES_HOST` / `POSTGRES_PORT` | Connexion PostgreSQL | `127.0.0.1` / `5432` |
| `PRIVATE_MEDIA_ROOT` | Répertoire des documents privés | `private_media` |
| `ARCHIVE_MAX_UPLOAD_SIZE` | Taille maximale d’upload | `10485760` |
| `ARCHIVE_ALLOWED_EXTENSIONS` | Extensions autorisées | `.pdf,.doc,.docx,.xls,.xlsx,.txt,.jpg,.jpeg,.png` |

Les variables HTTPS, cookies et HSTS sont décrites dans [`docs/environment.md`](docs/environment.md) et [`docs/installation.md`](docs/installation.md).

## Migrations, lancement et tests

```bash
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py runserver
python manage.py test
```

La commande de test exécute **263 tests**. Le contrôle de déploiement local signale volontairement les paramètres HTTPS et DEBUG non adaptés au développement HTTP :

```bash
python manage.py check --deploy
```

Un profil de production simulé avec hôte explicite, HTTPS, cookies secure et HSTS est documenté dans la revue sécurité. Aucun résultat `pip-audit` n’est revendiqué localement lorsque cet outil n’est pas installé.

## Comptes et rôles conceptuels

| Rôle | Périmètre documentaire | Actions principales |
|---|---|---|
| Consultant | PUBLIC | Consulter, rechercher, télécharger et vérifier l’intégrité d’une archive PUBLIC visible |
| Agent d’archives | PUBLIC, INTERNAL | Ajouter et modifier PUBLIC/INTERNAL, consulter, télécharger et vérifier les archives visibles |
| Administrateur | PUBLIC, INTERNAL, CONFIDENTIAL | Gestion documentaire complète dans le périmètre MVP et consultation de l’audit |
| Superuser technique | Accès technique complet | Administration Django selon les attributs Django explicites |

La matrice exhaustive se trouve dans [`docs/final-rbac-matrix.md`](docs/final-rbac-matrix.md). Les comptes de démonstration sont créés localement avec des données synthétiques ; aucun mot de passe de démonstration n’est versionné.

## Structure du dépôt

```text
accounts/       identité, rôles et authentification
archives/       domaine documentaire, RBAC, fichiers et intégrité
audit/          journal métier
dashboard/      métriques visibles
config/         paramètres et routes racines
templates/      gabarits Django
static/         CSS local de l’interface
tests/          tests transverses, sécurité et interface
docs/           documentation académique, technique et de démonstration
```

## Limites et perspectives

Les limites finales incluent l’absence de MFA, rate limiting intégré, antivirus, suppression physique, versioning documentaire, chiffrement applicatif au repos, signature numérique, SIEM/WORM, ACL de service/individu, pentest externe et certification OWASP.

Les perspectives possibles, après validation des besoins et des risques, sont le MFA, une protection anti-brute-force, un antivirus, du stockage objet privé, la rétention/versioning, les ACL fines, SIEM/WORM, signature numérique, monitoring, sauvegarde/restauration et un audit de dépendances en CI.

## Documentation

| Document | Contenu |
|---|---|
| [`docs/installation.md`](docs/installation.md) | Installation reproductible et lancement local |
| [`docs/architecture-final.md`](docs/architecture-final.md) | Architecture finale et modèle de données |
| [`docs/final-feature-matrix.md`](docs/final-feature-matrix.md) | Capacités intégrées, preuves et limites |
| [`docs/final-rbac-matrix.md`](docs/final-rbac-matrix.md) | Matrice par rôle et confidentialité |
| [`docs/final-test-matrix.md`](docs/final-test-matrix.md) | Couverture des 263 tests |
| [`docs/security-review.md`](docs/security-review.md) | Revue sécurité, modèle de menace et risques résiduels |
| [`docs/user-guide.md`](docs/user-guide.md) | Parcours Consultant, Agent et Administrateur |
| [`docs/demo-script.md`](docs/demo-script.md) | Scripts de démonstration 2 minutes et 5–7 minutes |
| [`docs/demo-evidence.md`](docs/demo-evidence.md) | Preuves et replis de démonstration |
| [`docs/presentation-outline.md`](docs/presentation-outline.md) | Plan de soutenance |
| [`docs/jury-questions.md`](docs/jury-questions.md) | Questions et réponses de jury |
| [`docs/steven-final-defense.md`](docs/steven-final-defense.md) | Fiche de révision finale |

## Licence

Les modalités de licence et de propriété intellectuelle restent à définir avec C-Tech et l’établissement académique.
