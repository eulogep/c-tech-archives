# Matrice finale des tests automatisés

La suite automatisée du MVP contient **280 tests**. Les nombres ci-dessous sont dérivés des fonctions de test réellement présentes dans les modules concernés. Cette matrice synthétise la couverture ; elle ne remplace pas l’exécution de `python manage.py test`.

| Groupe | Nombre | Objectif | Exemples de preuve |
|---|---:|---|---|
| Configuration et fondations | 5 | Vérifier l’enregistrement des applications, la configuration PostgreSQL, les répertoires partagés et les réglages de sécurité initiaux | `ProjectConfigurationTests` |
| Authentification | 27 | Vérifier session Django, connexion, compte inactif, redirection `next`, CSRF, déconnexion et bootstrap privilégié | `accounts/tests.py`, `HARD-019`, `HARD-020`, `HARD-024` |
| Dashboard | 10 | Vérifier les métriques et le respect du périmètre de visibilité | `dashboard/tests.py`, `RBAC-035` à `RBAC-038` |
| Modèles, CRUD et formulaires | Inclus dans les 144 tests archives | Vérifier contraintes, références, formulaires à liste blanche, création et modification | Tests archive de T-004 et T-008 |
| Recherche et filtres | Inclus dans les 144 tests archives | Vérifier GET, filtres combinables, pagination, query string, XSS et entrées SQL-like | `SEARCH-001` à `SEARCH-024` |
| Fichiers privés | Inclus dans les 144 tests archives | Vérifier upload synthétique, allowlist, taille, signatures, UUID, private storage et téléchargement | `FILE-001` à `FILE-020` |
| RBAC et confidentialité | Inclus dans les 144 tests archives | Vérifier visibilité PUBLIC/INTERNAL/CONFIDENTIAL, création, modification, téléchargement et non-inférence | `RBAC-001` à `RBAC-040` |
| Intégrité SHA-256 | Inclus dans les 144 tests archives | Vérifier calcul, états d’intégrité, POST CSRF, audit et absence de recalcul implicite | `HASH-001` à `HASH-024` |
| Audit métier | 30 | Vérifier événements, données minimales, permissions, pagination et Admin read-only | `AUDIT-001` à `AUDIT-030` |
| Durcissement sécurité | 26 | Vérifier IDOR, mass assignment, CSRF, XSS, injection-like, traversal, secrets et configuration production | `HARD-001` à `HARD-026` |
| Interface et accessibilité légère | 38 | Vérifier navigation par rôle, formulaires, composants critiques, états vides, landmarks et UI polish | `UI-001` à `UI-038` |

| Module de test | Nombre de tests |
|---|---:|
| `accounts/tests.py` | 27 |
| `archives/tests.py` | 144 |
| `audit/tests.py` | 30 |
| `dashboard/tests.py` | 10 |
| `tests/test_project.py` | 5 |
| `tests/test_security_hardening.py` | 26 |
| `tests/test_final_ui.py` | 21 |
| `tests/test_ui_polish.py` | 17 |
| **Total** | **280** |

## Lecture des résultats

La suite utilise des utilisateurs, archives et fichiers synthétiques. Les tests de fichiers emploient des stockages temporaires. Les matrices de test démontrent les comportements applicatifs ; elles ne constituent ni un pentest externe, ni une certification OWASP, ni une certification WCAG.
