# Matrice finale des fonctionnalités et preuves

Cette matrice décrit l’état réellement intégré du MVP C-Tech Archives après T-015. Chaque ligne relie une capacité observable à un module, une preuve automatisée et un parcours de démonstration. Elle ne transforme pas une perspective en fonctionnalité livrée.

| Fonction | Ticket | Code principal | Tests automatisés | Démonstration | Limite explicite |
|---|---|---|---|---|---|
| Authentification par session | T-006 | `accounts`, `LoginView`, `LogoutView` | `accounts/tests.py`, `HARD-019`, `HARD-020`, `HARD-024` | Connexion, navigation protégée, déconnexion | Pas de MFA ni rate limiting intégré |
| Rôles métier | T-003, T-011 | `accounts.models.Role`, `archives.permissions` | `accounts/tests.py`, `archives/tests.py` | Connexion avec Consultant, Agent, Administrateur | Politique MVP à valider avec C-Tech ; pas d’ACL nominative |
| Dashboard RBAC | T-007, T-011 | `dashboard.views`, `visible_archives_for` | `dashboard/tests.py`, `RBAC-035` à `RBAC-038`, `UI-008` | Comparer les métriques d’un Consultant et d’un Administrateur | Pas de widgets analytiques ni statistiques historiques |
| CRUD des métadonnées | T-008, T-011 | `archives.views`, `ArchiveForm`, `archives.access` | `archives/tests.py`, `RBAC-019` à `RBAC-028` | Créer puis modifier une archive autorisée | Pas de suppression physique ni remplacement libre du fichier |
| Recherche et filtres | T-009, T-011 | `ArchiveListView`, `ArchiveSearchForm` | `SEARCH-001` à `SEARCH-024`, `UI-010`, `UI-011` | Rechercher par texte, service et statut | Pas de recherche plein texte ou sémantique |
| Stockage privé et upload contrôlé | T-010 | `archives.storage`, `ArchiveForm.clean_file` | `FILE-001` à `FILE-020`, `HARD-009` à `HARD-011` | Déposer un PDF synthétique puis consulter la fiche | Pas d’antivirus ni inspection exhaustive des formats Office |
| Téléchargement contrôlé | T-010, T-011 | `ArchiveDownloadView`, `FileResponse`, `can_download_archive` | `FILE-011` à `FILE-016`, `RBAC-029` à `RBAC-034` | Télécharger un document visible avec un rôle autorisé | Pas de diffusion directe par `MEDIA_URL` ni serveur de fichiers optimisé |
| RBAC et confidentialité | T-011 | `archives.permissions`, QuerySets visibles, mixins | `RBAC-001` à `RBAC-040`, `HARD-001` à `HARD-004` | Montrer PUBLIC, INTERNAL et CONFIDENTIAL selon le rôle | Pas d’ACL par service, individu ou délégation temporaire |
| Audit métier append-only applicatif | T-012 | `audit.models`, `audit.services`, `audit.views` | `AUDIT-001` à `AUDIT-030`, `HARD-012` à `HARD-014` | Consulter le journal comme Administrateur | Pas de SIEM, WORM ou immutabilité externe |
| Intégrité SHA-256 | T-013 | `archives.integrity`, `ArchiveIntegrityVerifyView` | `HASH-001` à `HASH-024`, `HARD-018` | Vérifier une archive et expliquer `VALID`/`MISMATCH` | Pas de signature numérique, chiffrement ou garantie contre compromission simultanée DB/stockage |
| Durcissement sécurité | T-014 | `config.settings`, politiques, vues et services existants | `HARD-001` à `HARD-026` | Présenter RBAC, CSRF, stockage privé, audit et profil de production simulé | Pas de pentest externe, certification OWASP ou scanner de dépendances exécuté localement |
| Interface responsive | T-015 | `templates/`, `static/css/app.css` | `UI-001` à `UI-021` | Connexion, dashboard, recherche, fiche, audit et adaptation d’écran | Revue d’accessibilité légère ; pas de certification WCAG ni test pixel-perfect |

## Lecture de la preuve

Les tests regroupés sont conservés dans les applications métier et dans `tests/`. La commande `python manage.py test` exécute actuellement **255 tests**. La démonstration doit employer uniquement des données synthétiques ; les exemples de comptes, de services et de documents ne doivent jamais correspondre à des données réelles de C-Tech.

> Une action masquée dans l’interface améliore l’expérience du rôle concerné. Elle ne constitue pas la preuve de sécurité : les autorisations sont imposées par les QuerySets, les mixins, les vues, les formulaires et les services côté serveur.
