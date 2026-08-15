# Matrice RBAC finale du MVP

La politique ci-dessous est la règle effectivement appliquée par `archives.permissions`. Elle reste un **MVP provisoire à valider avec C-Tech** : le projet ne fournit pas d’ACL par service, par individu, par délégation ou par durée.

| Action | Administrateur | Agent d’archives | Consultant | Preuve serveur |
|---|---|---|---|---|
| Tableau de bord | Oui, métriques de tous les niveaux | Oui, métriques PUBLIC et INTERNAL | Oui, métriques PUBLIC | `visible_archives_for` avant les agrégations |
| Liste d’archives | PUBLIC, INTERNAL, CONFIDENTIAL | PUBLIC, INTERNAL | PUBLIC | QuerySet filtré avant liste, recherche et pagination |
| Recherche et filtres | Tous les niveaux visibles | PUBLIC et INTERNAL | PUBLIC | `ArchiveListView` sur QuerySet visible |
| Détail PUBLIC | Oui | Oui | Oui | `can_view_archive` et mixin de QuerySet visible |
| Détail INTERNAL | Oui | Oui | Non, HTTP 404 | Anti-inférence par QuerySet visible |
| Détail CONFIDENTIAL | Oui | Non, HTTP 404 | Non, HTTP 404 | Anti-inférence par QuerySet visible |
| Création | Oui, tous niveaux | Oui, PUBLIC et INTERNAL | Non, HTTP 403 | `can_create_archive` et `can_assign_confidentiality` |
| Modification PUBLIC | Oui | Oui | Non, HTTP 403 | `can_update_archive` |
| Modification INTERNAL | Oui | Oui | Non, non visible | `can_update_archive` et QuerySet visible |
| Modification CONFIDENTIAL | Oui | Non, HTTP 404 | Non, HTTP 404 | `can_update_archive` et QuerySet visible |
| Téléchargement PUBLIC | Oui | Oui | Oui | `can_download_archive` et `ArchiveDownloadView` |
| Téléchargement INTERNAL | Oui | Oui | Non, HTTP 404 | Même visibilité que le détail |
| Téléchargement CONFIDENTIAL | Oui | Non, HTTP 404 | Non, HTTP 404 | Même visibilité que le détail |
| Vérification d’intégrité | Oui sur archive visible | Oui sur archive visible | Oui sur archive visible | POST CSRF et QuerySet visible |
| Consultation du journal d’audit | Oui | Non, HTTP 403 | Non, HTTP 403 | `audit.views` et `audit_policy` |
| Administration technique Django | Selon `is_staff`/`is_superuser` explicite | Non par rôle métier seul | Non par rôle métier seul | Permissions Django standard |

Un superuser Django bénéficie de l’accès technique complet et de tous les niveaux documentaires. Il reste distinct du rôle métier `ADMINISTRATEUR` : attribuer un rôle métier ne confère pas implicitement les attributs `is_staff` ou `is_superuser`.

## Politique de réponse 404 et 403

Une archive hors du périmètre visible répond **404** afin de ne pas confirmer son existence. Une archive déjà visible mais pour laquelle l’action est interdite répond **403**. Cette distinction est couverte par les tests RBAC et de durcissement ; elle ne doit pas être neutralisée par l’interface utilisateur.
