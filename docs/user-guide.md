# Guide utilisateur du MVP

## Avant de commencer

L’application est destinée à une utilisation interne. Connectez-vous avec un compte local créé par l’administrateur de démonstration ou par la procédure Django prévue. Les droits réels sont vérifiés côté serveur ; l’interface adapte seulement les actions visibles à votre rôle.

Les exemples de services, catégories, types de documents et archives doivent être synthétiques. Ne saisissez pas de données réelles C-Tech dans un environnement de démonstration.

## Parcours Consultant

Le Consultant consulte exclusivement les archives **PUBLIC**. Après la connexion, il accède au tableau de bord puis à l’écran **Archives**. Il peut rechercher par texte, service, catégorie, type, statut, confidentialité et intervalle de dates parmi les éléments visibles. Une archive INTERNAL ou CONFIDENTIAL n’apparaît pas dans sa liste et une URL directe hors périmètre répond de façon générique.

Sur une archive PUBLIC visible, le Consultant peut ouvrir la fiche, télécharger le document via la vue protégée et lancer la vérification d’intégrité. Le bouton de vérification soumet une requête POST protégée par CSRF ; un message indique le résultat, par exemple `VALID` lorsque le contenu correspond à l’empreinte de référence. Le Consultant ne peut ni créer, ni modifier une archive, ni consulter le journal d’audit.

Pour terminer la session, utilisez le bouton **Déconnexion** de l’en-tête. Cette action reste un formulaire POST protégé par CSRF.

## Parcours Agent d’archives

L’Agent voit les archives **PUBLIC** et **INTERNAL**. Il dispose des mêmes parcours de recherche, consultation, téléchargement et vérification d’intégrité pour ce périmètre. Il peut créer une archive et modifier les métadonnées d’une archive visible, à condition de conserver un niveau de confidentialité autorisé.

Pour créer une archive, ouvrez **Nouvelle archive**, complétez les sections Identification et Classification, puis joignez si nécessaire un fichier. Le serveur contrôle l’extension, la taille, le type déclaré lorsqu’il est disponible et certaines signatures de format. Le fichier est écrit dans le stockage privé ; son nom physique n’est pas déterminé par le nom envoyé par le navigateur.

Lors de la modification, les champs techniques tels que l’auteur, la taille, l’empreinte et les horodatages restent gérés par le serveur. Le remplacement d’un fichier existant n’est pas disponible dans le MVP, car aucune politique de versioning n’a été validée. L’Agent ne voit ni les archives CONFIDENTIAL ni le journal d’audit.

## Parcours Administrateur

L’Administrateur voit les trois niveaux : **PUBLIC**, **INTERNAL** et **CONFIDENTIAL**. Il peut créer et modifier les archives dans ce périmètre, rechercher l’ensemble des archives visibles, télécharger les documents autorisés et vérifier leur intégrité.

L’Administrateur accède également au **Journal d’audit**. Cette page présente les événements métier : date, utilisateur, action, référence d’archive et adresse IP lorsqu’elle est disponible. Les détails sensibles, tels que mots de passe, session, cookie, checksum complet, contenu et chemin privé, ne sont pas affichés.

Le rôle métier Administrateur est distinct des privilèges techniques Django. Seul un compte disposant explicitement de `is_staff` ou `is_superuser` peut utiliser l’administration Django selon les permissions du framework.

## Recherche et pagination

La recherche est une lecture et utilise GET. Les critères restent visibles dans l’URL et sont conservés lorsque vous changez de page. Utilisez **Réinitialiser** pour revenir à la liste sans filtre. Un état vide distinct indique qu’aucune archive n’est disponible dans le périmètre ou qu’aucun résultat ne correspond aux critères.

## Signification des statuts et badges

| Élément | Signification |
|---|---|
| Active | Archive actuellement suivie dans le MVP |
| Archivée | Archive marquée comme archivée, sans suppression physique |
| Public | Visible à tous les rôles métier authentifiés reconnus |
| Interne | Visible à l’Agent et à l’Administrateur |
| Confidentiel | Visible uniquement à l’Administrateur et au superuser technique |
| `VALID` | Le fichier actuel correspond à l’empreinte SHA-256 de référence |
| `MISMATCH` | Le fichier actuel ne correspond plus à l’empreinte de référence ; la référence historique est conservée |

## Limites à connaître

Le MVP ne propose pas de suppression physique, de versioning de fichier, d’antivirus, de MFA, de partage externe, de notification, d’ACL par service ou utilisateur, ni de chiffrement applicatif au repos. Ces limites doivent être expliquées comme des choix de périmètre, non comme des garanties absentes par oubli.
