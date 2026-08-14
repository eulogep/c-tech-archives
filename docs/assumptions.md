# Hypothèses métier à valider — C-Tech Archives

> Ce document distingue les choix provisoires nécessaires au MVP des règles métier validées. Aucune hypothèse ne doit être présentée comme une politique définitive de C-Tech avant confirmation par l’organisation.

| ID | Description | Statut | Impact technique | Validation C-Tech |
|---|---|---|---|---|
| A-001 | C-Tech possède plusieurs services organisationnels auxquels les archives peuvent être rattachées. | Provisoire | Modèle `Service` actif/inactif, relation obligatoire protégée avec `Archive`. | Requis avant la configuration de la liste officielle des services. |
| A-002 | Chaque archive appartient à une catégorie documentaire générale. | Provisoire | Modèle `Category` distinct, relation obligatoire protégée avec `Archive`. | Requis avant l’import de référentiels réels. |
| A-003 | Chaque archive possède un type documentaire plus précis que sa catégorie. | Provisoire | Modèle `DocumentType` distinct, relation obligatoire protégée avec `Archive`. | Requis pour confirmer que la distinction est utile et définir les valeurs réelles. |
| A-004 | Trois niveaux de confidentialité provisoires suffisent au MVP : `PUBLIC`, `INTERNAL` et `CONFIDENTIAL`. | Provisoire | `ConfidentialityLevel` avec contrainte de base de données ; aucune permission associée à ce stade. | Requis avant l’implémentation des règles d’accès. |
| A-005 | Une référence documentaire provisoire peut suivre le format `CT-AAAA-NNNNNN`, par exemple `CT-2026-000001`. | Provisoire | Champ `reference` unique ; génération automatique volontairement absente. | Requis avant toute génération de référence ou import de données. |
| A-006 | Un service, une catégorie ou un type devenu inutilisé doit être désactivé plutôt que supprimé lorsqu’il est référencé. | Provisoire | Champ `is_active` et relations `PROTECT` pour préserver l’historique. | Requis avant toute politique de purge ou d’archivage des référentiels. |

## Distinction retenue pour le MVP

Une **catégorie** est un classement documentaire large, tel que « Contrat », « Facture » ou « Rapport ». Un **type de document** est une qualification métier plus précise, éventuellement dépendante d’une convention future de C-Tech, telle que « Contrat de prestation » ou « Facture fournisseur ». Les deux référentiels restent séparés afin de ne pas perdre cette capacité de précision. Si C-Tech ne confirme pas cette distinction, `DocumentType` pourra être simplifié dans une évolution ultérieure, mais aucune hiérarchie artificielle n’est introduite dans T-004.

## Visibilité des métriques du dashboard — T-007

Les six métriques globales du dashboard sont provisoirement visibles par tout utilisateur authentifié. **À valider avec C-Tech avant T-011 :** ces compteurs doivent-ils rester globaux pour tous les rôles, être filtrés par service, ou être réservés à certains profils ? Aucune règle partielle n’est implémentée avant la définition complète du RBAC et de la confidentialité documentaire.


## Fichiers et stockage privé — T-010

| ID | Description | Statut | Impact technique | Validation C-Tech |
|---|---|---|---|---|
| A-007 | Les formats `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.txt`, `.jpg`, `.jpeg` et `.png` couvrent provisoirement les besoins documentaires du MVP. | Provisoire | Allowlist configurable dans `ARCHIVE_ALLOWED_EXTENSIONS`; les exécutables et scripts ne sont pas acceptés. | Requis avant mise en production et avant l’ajout d’un format. |
| A-008 | Une limite de 10 MiB par document est acceptable pour le développement du MVP. | Provisoire | `ARCHIVE_MAX_UPLOAD_SIZE=10485760`, contrôle serveur avant persistance. | Requis pour définir la limite opérationnelle et les éventuelles exceptions. |
| A-009 | Un stockage local privé suffit au MVP tant qu’il n’est exposé par aucune URL publique. | Provisoire | `PRIVATE_MEDIA_ROOT`, noms physiques UUID, diffusion exclusivement par vue Django contrôlée. | Requis pour choisir le stockage de production, les sauvegardes et la rétention. |
| A-010 | Le remplacement d’un fichier ne doit pas être autorisé sans politique de versioning, de conservation et de traçabilité. | Provisoire | Le champ `file` est retiré du formulaire de modification des métadonnées. | Requis avant toute fonctionnalité de remplacement ou de versionnage. |

Une archive historique peut temporairement ne pas avoir de fichier associé. Le chemin fonctionnel normal à partir de T-010 permet toutefois de joindre un document à la création. La validation de format et de taille réduit les risques mais ne constitue ni un antivirus ni une garantie que le contenu est sûr.
