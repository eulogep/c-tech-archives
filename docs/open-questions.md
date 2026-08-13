# Informations à confirmer avec C-Tech

Les points suivants ne doivent pas être inventés. Ils constituent des questions de cadrage et conditionnent certaines règles métier et de sécurité du futur MVP.

| Sujet | Questions à valider | Impact projet |
|---|---|---|
| Services | Quels services ou départements existent ? Un utilisateur appartient-il à un seul service ? | Référentiel `Service`, filtres et visibilité |
| Types de documents | Quels types sont officiellement gérés ? | Référentiel `DocumentType`, validation et recherche |
| Catégories | Quelles catégories sont nécessaires et qui peut les administrer ? | Référentiel `Category`, formulaires et droits |
| Confidentialité | Quels niveaux utiliser ? L’accès dépend-il du rôle, du service ou d’une autorisation nominative ? | Règles RBAC/ACL, requêtes et téléchargement |
| Cycle de vie | Quels statuts d’archive existent ? Une archive est-elle supprimée, désactivée ou conservée selon une durée ? | Champ `status`, suppression logique, audit |
| Conservation | Quelle durée de conservation s’applique par type de document ? | Perspectives de rétention et purge contrôlée |
| Volumétrie | Nombre de documents, taille moyenne/maximale et croissance attendue ? | Limites d’upload, stockage, index et infrastructure |
| Formats | Quelles extensions sont acceptées ou interdites ? | Liste blanche de validation des fichiers |
| Nommage | Existe-t-il une convention de référence documentaire ? | Génération ou validation de `Archive.reference` |
| Identité | Les utilisateurs auront-ils un compte local ou une source d’identité existante ? | Création des comptes, authentification future |
| Conformité | Quelles obligations locales, contractuelles ou internes portent sur les données et archives ? | Politique d’accès, rétention, traçabilité et déploiement |
| Déploiement | Où l’application sera-t-elle hébergée et qui l’administrera ? | Réglages HTTPS, stockage, sauvegardes et exploitation |

## Décisions provisoires acceptables pour le développement

Tant que les réponses ne sont pas disponibles, le projet peut commencer avec trois rôles, les référentiels administrables, une référence unique librement saisie ou générée, des fichiers de démonstration non sensibles et un stockage local privé en développement. Ces hypothèses doivent être libellées comme **provisoires** dans les démonstrations et révisées dès qu’un interlocuteur de C-Tech confirme les règles réelles.
