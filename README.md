# Plateforme web sécurisée de gestion des archives — C-Tech

> **Projet académique de Génie Informatique (3e année).** Cette plateforme vise à centraliser, sécuriser et tracer la gestion des archives de C-Tech, sans présumer de processus métier non encore validés par l’organisation.

## État du projet

Le dépôt est initialisé avec la **conception fonctionnelle et technique préalable au code**. Cette approche permet de conserver un lien démontrable entre les besoins, les choix de conception, les tests et les futures itérations Git.

| Élément | État |
|---|---|
| Analyse du besoin et périmètre MVP | Préparé |
| Architecture, données, sécurité et tests | Documentés |
| Roadmap par tickets | Préparée |
| T-001 — Initialisation Django | Terminé et intégré à `develop` |
| T-002 — PostgreSQL et environnement | Terminé et intégré à `develop` |
| T-003 — Utilisateur personnalisé et rôles | Terminé et intégré à `develop` |
| T-004 — Modèles métier fondamentaux des archives | Terminé et intégré à `develop` |
| T-005 — Migrations et administration | **ABSORBED_BY_T004** ; clôture documentaire, sans code métier supplémentaire |
| T-006 — Authentification sécurisée | **INTEGRATED** dans `develop` |
| T-007 — Tableau de bord | **INTEGRATED** dans `develop` ; indicateurs agrégés uniquement avant RBAC T-011 |
| T-008 — CRUD des métadonnées d’archives | **INTEGRATED** dans `develop` ; accès technique temporairement restreint aux comptes staff |
| T-009 — Recherche et filtres d’archives | **INTEGRATED** dans `develop` ; recherche GET ORM et filtres de métadonnées accessibles aux comptes staff |
| T-010 — Téléversement et téléchargement sécurisés | **INTEGRATED** dans `develop` ; stockage privé, validation serveur et téléchargement contrôlé |
| T-011 — RBAC et confidentialité | **INTEGRATED** dans `develop` ; droits métier centralisés et visibilité filtrée au niveau QuerySet |
| T-012 — Journal d’audit | **INTEGRATED** dans `develop` ; événements métier structurés, append-only et consultation administrateur |
| T-013 — Intégrité SHA-256 | **INTEGRATED** dans `develop` ; empreinte calculée à l’upload et vérification contrôlée à la demande |
| T-014 — Tests de sécurité et durcissement final | **INTEGRATED** dans `develop` ; revue transverse, matrice HARD-001 à HARD-026 et risques résiduels documentés |
| T-015 — Interface utilisateur finale | **IN_REVIEW** sur `feature/final-ui` ; PR #15 ouverte, refonte responsive, accessibilité légère et aucune modification métier |
| Application Django | Socle modulaire, PostgreSQL, modèle utilisateur, authentification par session, CRUD, recherche, stockage privé, RBAC, audit métier, contrôle d’intégrité SHA-256, couverture de sécurité transverse et interface responsive configurés |

## Objectif du MVP

Le MVP permettra à des utilisateurs authentifiés de gérer des archives et leurs métadonnées, selon des droits contrôlés côté serveur. Les actions sensibles seront journalisées et chaque fichier déposé recevra une empreinte SHA-256 permettant un contrôle ultérieur de son intégrité.

Les rôles prévus sont **Administrateur**, **Agent d’archives** et **Consultant**. L’application s’appuie sur Django, PostgreSQL, Django Templates et une feuille CSS locale centralisée. Le frontend reste intégré à Django pendant le MVP.

## Architecture cible

```text
c-tech-archives/
├── config/                 # Configuration Django, réglages par environnement
├── accounts/               # Utilisateur personnalisé, rôles et gestion des comptes
├── archives/               # Archives, catégories, services, types de document
├── audit/                  # Journal d’audit applicatif
├── dashboard/              # Indicateurs et vue d’accueil
├── templates/              # Gabarits Django partagés
├── static/                 # Ressources statiques locales, dont le design system CSS
├── media/                  # Ressources média génériques de développement — non versionnées
├── private_media/          # Documents d’archives privés — non versionnés, non exposés
├── tests/                  # Tests transversaux et de sécurité
├── docs/                   # Documentation pour le mémoire
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

La logique métier ne devra pas être concentrée dans une seule application. Les frontières fonctionnelles sont décrites dans [`docs/architecture.md`](docs/architecture.md).

## Démarrage local après T-001

Le socle Django est initialisé. Les commandes suivantes permettent de l’exécuter localement ; PostgreSQL et les modèles métier seront ajoutés dans les tickets suivants. Pendant T-001, SQLite reste une solution temporaire de démarrage.

```bash
git clone https://github.com/eulogep/c-tech-archives.git
cd c-tech-archives
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

## Documentation

| Document | Contenu |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Architecture modulaire, composants et flux principaux |
| [`docs/database.md`](docs/database.md) | Modèles Django, MCD et MLD initiaux |
| [`docs/security.md`](docs/security.md) | Exigences et mesures de sécurité du MVP |
| [`docs/use-cases.md`](docs/use-cases.md) | Cas d’utilisation et acteurs |
| [`docs/roadmap.md`](docs/roadmap.md) | Tickets séquentiels et conditions de passage |
| [`docs/tests.md`](docs/tests.md) | Stratégie de test et matrice de couverture |
| [`docs/decisions.md`](docs/decisions.md) | Journal des décisions techniques pour le mémoire |
| [`docs/open-questions.md`](docs/open-questions.md) | Informations métier et organisationnelles à valider avec C-Tech |
| [`docs/technical-validation-questions.md`](docs/technical-validation-questions.md) | Décisions techniques à valider avant intégration et déploiement |
| [`docs/environment.md`](docs/environment.md) | Configuration PostgreSQL et exigences d’environnement de production |
| [`docs/assumptions.md`](docs/assumptions.md) | Hypothèses métier C-Tech à confirmer avant les règles définitives |
| [`docs/tickets/T-001.md`](docs/tickets/T-001.md) | Compte rendu de clôture du ticket d’initialisation |
| [`docs/tickets/T-002.md`](docs/tickets/T-002.md) | Compte rendu de clôture du ticket PostgreSQL et environnement |
| [`docs/tickets/T-003.md`](docs/tickets/T-003.md) | Compte rendu de clôture du ticket utilisateur personnalisé et rôles |
| [`docs/tickets/T-004.md`](docs/tickets/T-004.md) | Compte rendu de clôture du ticket modèles métier fondamentaux |
| [`docs/tickets/T-005.md`](docs/tickets/T-005.md) | Clôture documentaire du ticket absorbé par T-004 |
| [`docs/tickets/T-006.md`](docs/tickets/T-006.md) | Compte rendu de clôture du ticket authentification sécurisée |
| [`docs/tickets/T-007.md`](docs/tickets/T-007.md) | Compte rendu du ticket tableau de bord intégré après correction de revue |
| [`docs/tickets/T-008.md`](docs/tickets/T-008.md) | Compte rendu du ticket CRUD des métadonnées intégré |
| [`docs/tickets/T-009.md`](docs/tickets/T-009.md) | Compte rendu du ticket recherche et filtres d’archives intégré |
| [`docs/tickets/T-010.md`](docs/tickets/T-010.md) | Compte rendu du ticket téléversement et téléchargement sécurisés intégré |
| [`docs/tickets/T-011.md`](docs/tickets/T-011.md) | Compte rendu du ticket RBAC et confidentialité intégré |
| [`docs/tickets/T-012.md`](docs/tickets/T-012.md) | Compte rendu du ticket journal d’audit intégré |
| [`docs/tickets/T-013.md`](docs/tickets/T-013.md) | Compte rendu du ticket intégrité SHA-256 intégré |
| [`docs/security-review.md`](docs/security-review.md) | Revue de sécurité transverse, modèle de menace et risques résiduels |
| [`docs/steven-security-defense.md`](docs/steven-security-defense.md) | Fiche courte de défense sécurité pour la soutenance |
| [`docs/tickets/T-014.md`](docs/tickets/T-014.md) | Compte rendu du ticket tests de sécurité et durcissement intégré |
| [`docs/ui-guidelines.md`](docs/ui-guidelines.md) | Design system, responsive, composants et revue d’accessibilité légère |
| [`docs/tickets/T-015.md`](docs/tickets/T-015.md) | Compte rendu du ticket interface utilisateur finale en cours de revue |

## Convention Git

Le dépôt suivra une organisation simple : `main`, `develop`, `feature/*` et `fix/*`. Un ticket correspond à une branche de fonctionnalité, à des tests associés et à un commit explicite. Aucun ticket ne doit être considéré terminé si ses tests échouent.

Exemple de commit :

```text
feat(auth): add role-based authentication
```

## Hors périmètre du MVP

La blockchain, l’intelligence artificielle, l’OCR avancé, les applications mobiles, la signature électronique, les microservices, Kubernetes et l’architecture distribuée constituent des **perspectives** et ne seront pas implémentés dans le MVP.

## Licence

Les modalités de licence et de propriété intellectuelle restent à définir avec C-Tech et l’établissement académique. Aucune licence publique n’est déclarée à ce stade.
