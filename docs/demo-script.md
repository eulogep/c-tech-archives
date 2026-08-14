# Script de démonstration

## Préparation

Préparez uniquement des données synthétiques : **Service Direction Administrative**, **Service RH Démo**, **Catégorie Contrats Démo**, **Type Rapport Démo**, au moins une archive PUBLIC, une INTERNAL et une CONFIDENTIAL, ainsi que des comptes locaux Consultant, Agent et Administrateur. Ne montrez ni mot de passe, ni clé, ni chemin privé de stockage, ni données réelles C-Tech.

## Version complète — 5 à 7 minutes

| Temps indicatif | Étape | Action et formulation proposée |
|---|---|---|
| 0:00–0:30 | Contexte | « C-Tech Archives centralise les métadonnées et documents tout en contrôlant qui peut consulter, modifier ou télécharger une archive. » |
| 0:30–1:00 | Connexion | Montrer la page d’accès sécurisé. Expliquer que Django gère la session et que la déconnexion reste un POST protégé CSRF. |
| 1:00–1:30 | Consultant | Se connecter Consultant, ouvrir Archives et montrer qu’une archive PUBLIC est visible alors que les archives INTERNAL et CONFIDENTIAL ne sont pas listées. |
| 1:30–2:15 | Agent | Se connecter Agent, montrer l’accès PUBLIC/INTERNAL et l’absence de CONFIDENTIAL. Ouvrir Nouvelle archive pour montrer que l’action est disponible. |
| 2:15–3:00 | Recherche | Utiliser un terme `q`, un service et un statut. Montrer que la recherche reste en GET et que la pagination conserve les critères. |
| 3:00–3:45 | Fichier | Créer ou consulter une archive avec un PDF synthétique. Expliquer que le fichier est validé et stocké hors exposition publique ; le téléchargement passe par une vue contrôlée. |
| 3:45–4:30 | Intégrité | Ouvrir la fiche puis lancer Vérifier l’intégrité. Montrer `VALID`. Expliquer que `MISMATCH` signale une différence sans remplacer le checksum historique. |
| 4:30–5:15 | Administrateur et audit | Se connecter Administrateur, montrer l’archive CONFIDENTIAL et le journal d’audit. Souligner que l’audit affiche des détails minimaux. |
| 5:15–6:00 | Sécurité | Résumer RBAC, QuerySets filtrés, 404 anti-inférence, CSRF, stockage privé, audit et SHA-256. |
| 6:00–6:30 | Tests et limites | Montrer la suite de 263 tests. Terminer avec les limites : pas de MFA, antivirus, versioning, SIEM/WORM, chiffrement applicatif ou pentest externe. |

## Version courte — 2 minutes

| Temps indicatif | Étape | Message essentiel |
|---|---|---|
| 0:00–0:20 | Problème et connexion | « Le MVP centralise les archives avec une authentification par session et des rôles métier. » |
| 0:20–0:45 | Consultant | Montrer PUBLIC visible, INTERNAL/CONFIDENTIAL absents. « La visibilité est appliquée avant la liste et la recherche. » |
| 0:45–1:10 | Agent et fichier | Montrer l’action Nouvelle archive et une fiche avec téléchargement contrôlé. « Le fichier reste privé et validé côté serveur. » |
| 1:10–1:30 | Intégrité | Cliquer Vérifier l’intégrité et commenter `VALID`. « SHA-256 détecte une différence, ce n’est pas du chiffrement. » |
| 1:30–1:50 | Administrateur et audit | Montrer CONFIDENTIAL et Audit. « L’interface est adaptée au rôle, mais l’autorisation est toujours vérifiée côté serveur. » |
| 1:50–2:00 | Preuve | « Le projet possède 263 tests automatisés et documente ses limites de production. » |

## Conseils de démonstration

Préparez les comptes et archives synthétiques avant le passage. Gardez la matrice [`demo-evidence.md`](demo-evidence.md) disponible en cas de panne de navigateur, de session expirée ou de problème de fichier. Ne simulez pas une attaque destructrice sur l’environnement de démonstration ; expliquez plutôt les tests automatisés qui couvrent les contrôles négatifs.
