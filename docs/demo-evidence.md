# Preuves de démonstration

Cette grille prépare une démonstration robuste : chaque affirmation fonctionnelle s’appuie sur un comportement réel, une preuve automatisée et une solution de repli si le parcours visuel ne peut pas être montré en direct.

| Affirmation | Démonstration | Résultat attendu | Preuve technique | Repli si la démo échoue |
|---|---|---|---|---|
| La connexion utilise une session Django | Se connecter avec un compte de démonstration local | Accès au dashboard et nom du compte affiché | Tests d’authentification et `UI-001` | Montrer le formulaire POST/CSRF et les tests `accounts` |
| Un Consultant ne voit que PUBLIC | Se connecter Consultant puis ouvrir Archives | Archives INTERNAL/CONFIDENTIAL absentes | `RBAC-005` à `RBAC-018`, `HARD-001` | Exécuter ou montrer la matrice RBAC finale |
| Un Agent voit PUBLIC et INTERNAL | Se connecter Agent puis filtrer les archives | PUBLIC et INTERNAL présents ; CONFIDENTIAL absent | `RBAC-005` à `RBAC-028` | Montrer `archives.permissions` et les tests RBAC |
| Le tableau de bord respecte le rôle | Comparer le compteur visible entre Consultant et Administrateur | Les métriques correspondent au périmètre du rôle | `RBAC-035` à `RBAC-038`, `UI-008` | Montrer les assertions de test dashboard |
| La recherche est contrôlée | Rechercher un titre synthétique avec service et statut | Résultat filtré ; pagination conserve les critères | `SEARCH-001` à `SEARCH-024`, `UI-010`, `UI-011` | Montrer l’URL GET et les tests SEARCH |
| L’upload est validé et privé | Déposer un PDF synthétique avec Agent | Archive créée ; aucun lien public de stockage affiché | `FILE-001` à `FILE-020`, `UI-019` | Montrer `PrivateArchiveStorage` et les tests fichiers |
| Le téléchargement est autorisé | Télécharger un document visible | Pièce jointe servie par la vue contrôlée | `RBAC-029` à `RBAC-034` | Montrer la route `download/` et les tests RBAC |
| L’intégrité est vérifiable | Cliquer « Vérifier l’intégrité » sur une archive synthétique | Message `VALID` si le fichier est intact | `HASH-001` à `HASH-024`, `UI-015` | Expliquer les états documentés `VALID`/`MISMATCH` |
| L’audit est réservé à l’Administrateur | Se connecter Administrateur puis ouvrir Audit | Journal visible ; Agent et Consultant refusés | `AUDIT-020` à `AUDIT-029`, `UI-016` | Montrer la matrice audit et l’accès serveur |
| La sécurité est testée transversalement | Présenter le résultat de la suite de test | 263 tests réussis ; durcissement couvert | `HARD-001` à `HARD-026` | Exécuter `python manage.py test` ou montrer la sortie enregistrée |
| L’interface est responsive et guidée par le rôle | Réduire la fenêtre ou utiliser l’émulation navigateur | Navigation compacte, tables défilables, actions adaptées | `UI-002` à `UI-021`, `ui-guidelines.md` | Montrer les breakpoints dans `app.css` |

## Données de démonstration autorisées

Les services, catégories et documents montrés doivent être strictement synthétiques, par exemple **Service Direction Administrative**, **Service RH Démo**, **Catégorie Contrats Démo** et **Type Rapport Démo**. Les comptes et mots de passe de démonstration sont créés localement selon le guide d’installation ; ils ne doivent jamais être committés, affichés dans le mémoire ou réutilisés en production.
