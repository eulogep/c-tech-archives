# Guide d’interface — T-015

## Intention de conception

C-Tech Archives adopte une interface **sobre, institutionnelle et lisible**. Une plateforme documentaire interne doit permettre d’identifier rapidement une information, de comprendre les droits disponibles et de réaliser une action sans ajouter de distraction visuelle. La refonte reste rendue côté serveur avec Django Templates : elle ne modifie ni les modèles, ni le RBAC, ni le stockage privé, ni l’audit, ni le contrôle d’intégrité.

> Les éléments visuels adaptent l’expérience utilisateur ; les autorisations restent vérifiées par les QuerySets, mixins, vues et services serveur existants.

## Design system

| Élément | Choix | Usage |
|---|---|---|
| Couleur primaire | Bleu profond `#163b62` | Identité, boutons principaux, liens et structure de navigation |
| Surface | Blanc et gris clair | Lisibilité des cartes, formulaires, tableaux et zones de travail |
| Texte | Bleu-gris foncé | Contraste et confort de lecture prolongée |
| Succès | Vert `#176b4a` | Messages positifs et badge `ACTIVE`/`PUBLIC` |
| Information | Bleu `#1e5d8d` | Badge `ARCHIVED`/`INTERNAL` et informations secondaires |
| Avertissement | Orange `#9a5b06` | Badge `CONFIDENTIAL` et messages nécessitant une attention |
| Erreur | Rouge `#a52b31` | Erreurs de formulaire et alertes |
| Typographie | Stack système avec Inter en préférence | Aucune dépendance externe ou CDN nécessaire |
| Espacement | Échelle de `0,25rem` à `3rem` | Rythme commun entre les composants |
| Rayon et ombre | Arrondis modérés et ombres légères | Hiérarchie sans esthétique décorative excessive |

Les couleurs sont centralisées dans `static/css/app.css` avec des variables CSS. Les badges conservent toujours un libellé textuel, de sorte que la couleur ne soit jamais la seule information disponible.

## Structure et composants

Sur grand écran, l’application utilise une sidebar dédiée à la navigation authentifiée et une zone de contenu distincte. Sur tablette et mobile, la navigation devient une rangée compacte à défilement horizontal et la grille de contenu se replie. Le contenu principal reste accessible par un lien d’évitement clavier.

| Composant | Rôle | Comportement |
|---|---|---|
| Sidebar | Accès aux écrans pertinents | Les entrées sont affichées à partir des politiques de contexte existantes ; elles ne remplacent jamais les contrôles serveur |
| En-tête | Identité utilisateur et déconnexion | Le rôle lisible et le nom sont affichés ; la déconnexion reste un formulaire POST protégé CSRF |
| Cartes métriques | Synthèse du dashboard | Affichent uniquement les six métriques existantes du périmètre RBAC, sans statistiques inventées |
| Table responsive | Archives et audit | Défilement horizontal contrôlé sur petits écrans ; titres de colonnes et actions sémantiques conservés |
| Badges | Statut et confidentialité | Libellés visibles `Actif`, `Archivé`, `Public`, `Interne` et `Confidentiel` |
| Formulaires | Recherche et saisie | Labels associés, erreurs proches du champ, focus visible et validations serveur inchangées |
| États vides | Absence de données ou de résultats | Messages explicites plutôt que page ou tableau vide |
| Pages d’erreur | 403, 404 et 500 | Réponses neutres sans divulgation d’une ressource protégée |

## Responsive et accessibilité

Les règles CSS ciblent explicitement les largeurs proches de **1280 px**, **768 px** et **360 px**. Les grilles passent d’une présentation multi-colonnes à une colonne ; les tableaux restent consultables sans couper les données critiques grâce à un conteneur de défilement horizontal ; les groupes de boutons deviennent verticaux sur les écrans étroits.

La revue d’accessibilité T-015 est une **vérification légère**, et non une certification WCAG. Elle couvre les labels associés, les landmarks `nav` et `main`, les titres de page, un lien d’évitement, un focus `:focus-visible`, les rôles d’alerte utiles, les boutons et liens sémantiques, ainsi que des contrastes conçus pour distinguer texte, bordures et fonds. Les tests `UI-001` à `UI-021` contrôlent plusieurs de ces invariants structurels.

## Parcours de soutenance

Le parcours de démonstration recommandé est : connexion, tableau de bord, recherche d’archives, fiche documentaire, téléchargement contrôlé, vérification d’intégrité, puis journal d’audit administrateur. Il montre en moins de deux minutes le produit, les différences d’expérience selon le rôle et le fait que les contrôles de sécurité restent visibles sans être transformés en promesses excessives.

## Limites assumées

La refonte n’introduit pas de framework frontend, de JavaScript applicatif, d’animations complexes, de dépendance CDN critique, de statistiques de démonstration ni de test pixel-perfect. Elle ne constitue pas un audit WCAG complet. Les détails de conformité réglementaire, la charte graphique définitive de C-Tech et les besoins spécifiques d’assistance devront être validés avant un déploiement réel.
