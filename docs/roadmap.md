# Roadmap de développement

## Règle de réalisation

Les tickets sont exécutés **un par un**, sur une branche dédiée. À la fin de chaque ticket, les tests concernés doivent réussir. Le compte rendu de ticket respectera le format imposé : `TICKET`, `STATUS`, `FILES_CHANGED`, `TESTS`, `RESULT`, `SECURITY_IMPACT`, `NEXT_TICKET`, `GIT_COMMIT`.

| Ordre | Ticket | Objectif | Critère de sortie | Commit proposé |
|---:|---|---|---|---|
| 1 | T-001 | Initialisation Django | Projet initial, applications vides et configuration de base démarrent | `chore(project): initialize django structure` |
| 2 | T-002 | PostgreSQL et configuration environnement | Connexion PostgreSQL configurée par variables d’environnement ; secrets ignorés | `chore(config): add environment-based database settings` |
| 3 | T-003 | Utilisateur personnalisé et rôles | Modèle `User` et rôles migrés avant la première migration métier | `feat(accounts): add custom user roles` |
| 4 | T-004 | Modèles de référentiel et archive | Modèles `Service`, `Category`, `DocumentType`, `Archive` validés | `feat(archives): add core archive models` |
| 5 | T-005 | Migrations et administration | **ABSORBED_BY_T004** — migrations initiales appliquées et modèles administrables pendant T-004 ; aucun développement supplémentaire requis | Aucun commit dédié |
| 6 | T-006 | Authentification | Connexion, déconnexion, protection des vues et tests associés | `feat(auth): add secure authentication flow` |
| 7 | T-007 | Tableau de bord | Indicateurs, dernières archives et dernières actions selon droits | `feat(dashboard): add archive overview` |
| 8 | T-008 | CRUD des archives | Création, liste, détail, modification et suppression/désactivation contrôlées | `feat(archives): add archive management` |
| 9 | T-009 | Recherche et filtres | Recherche par référence, titre, catégorie, type, service et date | `feat(search): add archive filters` |
| 10 | T-010 | Téléversement sécurisé | Validation des fichiers, stockage privé et téléchargement protégé | `feat(files): secure archive uploads and downloads` |
| 11 | T-011 | RBAC et confidentialité | Contrôles serveur complets et refus testés pour chaque rôle | `feat(authz): enforce role-based archive access` |
| 12 | T-012 | Journal d’audit | Événements sensibles conservés et accessibles à l’administrateur | `feat(audit): log sensitive archive actions` |
| 13 | T-013 | Empreinte et vérification | SHA-256 calculé au dépôt et vérifiable ultérieurement | `feat(integrity): add archive checksum verification` |
| 14 | T-014 | Tests consolidés | Couverture des parcours critiques, droits, fichiers, audit et intégrité | `test: cover core archive security scenarios` |
| 15 | T-015 | Interface finale | Interface Bootstrap cohérente, responsive et accessible | `feat(ui): refine administrative interface` |
| 16 | T-016 | Documentation de démonstration | Documentation, décisions et éléments UML synchronisés avec le code | `docs: finalize technical and academic documentation` |

## Statut exceptionnel — T-005

> **ABSORBED_BY_T004.** Les migrations initiales et l’administration Django ont été implémentées pendant T-004 afin de permettre la validation réelle des modèles métier. L’audit sur `develop` confirme que `archives.0001_initial` est présente et appliquée, que `Service`, `Category`, `DocumentType`, `Archive` et `accounts.User` sont administrables, et que les contrôles Django ainsi que la suite de tests réussissent. Aucun développement supplémentaire n’était donc nécessaire pour T-005.

## Ordre d’implémentation obligatoire

T-001 ne débute qu’après validation de la présente conception initiale. Les changements de modèle avant T-003 doivent être particulièrement maîtrisés, car Django exige que le modèle utilisateur personnalisé soit déclaré avant les migrations qui le référencent.

## Format de clôture de ticket

```text
TICKET: T-XXX — [intitulé]
STATUS: DONE | BLOCKED
FILES_CHANGED: [liste]
TESTS: [commande et résultat]
RESULT: [résumé bref]
SECURITY_IMPACT: [contrôles ajoutés ou impact]
NEXT_TICKET: T-YYY — [intitulé]
GIT_COMMIT: [message proposé ou hash du commit]
```

Un statut `BLOCKED` doit identifier l’erreur, son impact et l’information ou l’action nécessaire avant de poursuivre. Aucun ticket suivant ne doit être traité silencieusement en cas d’échec de test du ticket courant.
