# Roadmap de développement

## Règle de réalisation

Les tickets sont exécutés **un par un**, sur une branche dédiée. À la fin de chaque ticket, les tests concernés doivent réussir. Le compte rendu de ticket respectera le format imposé : `TICKET`, `STATUS`, `FILES_CHANGED`, `TESTS`, `RESULT`, `SECURITY_IMPACT`, `NEXT_TICKET`, `GIT_COMMIT`.

| Ordre | Ticket | Objectif | État actuel | Critère de sortie principal |
|---:|---|---|---|---|
| 1 | T-001 | Initialisation Django | **INTEGRATED** | Projet Django modulaire initialisé |
| 2 | T-002 | PostgreSQL et configuration environnement | **INTEGRATED** | Connexion PostgreSQL et secrets par environnement |
| 3 | T-003 | Utilisateur personnalisé et rôles | **INTEGRATED** | Modèle `User` et rôles métier |
| 4 | T-004 | Modèles de référentiel et archive | **INTEGRATED** | `Service`, `Category`, `DocumentType` et `Archive` validés |
| 5 | T-005 | Migrations et administration | **ABSORBED_BY_T004** | Migrations initiales et administration réalisées pendant T-004 |
| 6 | T-006 | Authentification | **INTEGRATED** | Connexion, déconnexion, sessions et tests associés |
| 7 | T-007 | Tableau de bord | **INTEGRATED** | Six indicateurs agrégés limités au périmètre RBAC final |
| 8 | T-008 | CRUD des métadonnées d’archives | **INTEGRATED** | Création, liste, détail et modification ; aucune suppression physique |
| 9 | T-009 | Recherche et filtres | **INTEGRATED** | Recherche GET, filtres et pagination |
| 10 | T-010 | Téléversement sécurisé | **INTEGRATED** | Validation, stockage privé et téléchargement protégé |
| 11 | T-011 | RBAC et confidentialité | **INTEGRATED** | Contrôles serveur centralisés par rôle et confidentialité |
| 12 | T-012 | Journal d’audit | **INTEGRATED** | Événements métier minimaux et consultation administrateur |
| 13 | T-013 | Empreinte et vérification | **INTEGRATED** | SHA-256 calculé au dépôt et vérifiable par POST |
| 14 | T-014 | Tests consolidés | **INTEGRATED** | Durcissement, `HARD-001` à `HARD-026` et revue sécurité |
| 15 | T-015 | Interface finale | **INTEGRATED** | Interface responsive Django Templates et accessibilité légère |
| 16 | T-016 | Démonstration et documentation académique finale | **INTEGRATED** | Documentation, preuves et parcours de soutenance synchronisés avec le code |

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

## État final du périmètre académique

Les tickets T-001 à T-016 sont intégrés dans `develop`, à l’exception structurelle de T-005 qui reste **ABSORBED_BY_T004**. Aucun T-017 ni ticket obligatoire futur n’est créé par cette roadmap. Les évolutions telles que MFA, antivirus, versioning, ACL fine, stockage objet, SIEM/WORM ou monitoring demeurent des **perspectives produit** et non des livraisons réalisées.
