# Stratégie de tests

## Objectif

Les tests démontrent que les fonctionnalités attendues et les contrôles de sécurité réellement annoncés fonctionnent. Les tests automatisés utilisent le framework de tests Django. Ils seront exécutés à la clôture de chaque ticket et avant toute intégration vers `develop` ou `main`.

## Niveaux de test

| Niveau | Finalité | Exemples |
|---|---|---|
| Unitaire | Vérifier une règle isolée de modèle, formulaire ou service | Calcul SHA-256, validation d’extension, choix de rôle |
| Intégration | Vérifier plusieurs composants Django ensemble | Création d’archive, transaction et écriture d’audit |
| Vue / autorisation | Vérifier les réponses HTTP et permissions serveur | Utilisateur non authentifié, Consultant refusé, Administrateur autorisé |
| Régression | Conserver les scénarios critiques après corrections | Accès par URL de téléchargement devinée |

## Matrice de couverture cible

| Référence | Scénario | Résultat attendu | Ticket initial |
|---|---|---|---|
| TS-01 | Connexion valide | Redirection vers l’espace autorisé et session active | T-006 |
| TS-02 | Connexion invalide | Formulaire en erreur, aucune session créée | T-006 |
| TS-03 | Vue protégée sans session | Redirection vers la connexion ou refus approprié | T-006 |
| TS-04 | Création par Administrateur | Archive, fichier, checksum et audit créés | T-008/T-013 |
| TS-05 | Création par Agent d’archives | Création autorisée selon les règles | T-008/T-011 |
| TS-06 | Création par Consultant | Refus côté serveur | T-011 |
| TS-07 | Modification non autorisée | Réponse interdite ; aucune donnée modifiée | T-011 |
| TS-08 | Recherche multicritère | Seules les archives correspondant aux filtres et accessibles sont listées | T-009/T-011 |
| TS-09 | Téléchargement autorisé | Réponse fichier et événement d’audit | T-010/T-012 |
| TS-10 | Téléchargement via accès non autorisé | Refus ; fichier non servi | T-010/T-011 |
| TS-11 | Fichier interdit ou trop grand | Validation en erreur ; aucun stockage persistant | T-010 |
| TS-12 | Audit | Les actions `LOGIN`, `LOGOUT`, création, modification, consultation, téléchargement et suppression sont tracées | T-012 |
| TS-13 | Checksum intègre | Empreinte recalculée identique à la valeur stockée | T-013 |
| TS-14 | Checksum altéré | Écart détecté et signalé sans remplacer la valeur enregistrée | T-013 |

## Commandes prévues

Après T-001, les commandes de validation de base seront les suivantes :

```bash
python manage.py test
python manage.py check
```

Des commandes ciblées pourront être utilisées pendant un ticket, mais `python manage.py test` devra être lancé avant sa clôture. Toute erreur est documentée dans le compte rendu du ticket et résolue avant le ticket suivant.

## Données de test

Les fichiers de test seront synthétiques et de taille réduite. Aucun document réel de C-Tech, aucune donnée personnelle réelle et aucun secret ne doivent être ajoutés au dépôt ou aux jeux de tests.

## Couverture ajoutée par T-003

| Référence | Scénario | Résultat attendu |
|---|---|---|
| TS-15 | Résolution du modèle actif | `get_user_model()` retourne `accounts.User` |
| TS-16 | Création d’un utilisateur | Un compte valide est créé avec le rôle Consultant par défaut |
| TS-17 | Hachage de mot de passe | La valeur persistée diffère du mot de passe source et `check_password()` réussit |
| TS-18 | Rôles métier | Les valeurs Administrateur, Agent d’archives et Consultant sont acceptées |
| TS-19 | Rôle invalide | La validation et la contrainte PostgreSQL refusent une valeur hors choix |
| TS-20 | Compte inactif | `is_active=False` est conservé sans supprimer le compte |
| TS-21 | Rôle et superutilisateur | Un Administrateur métier n’obtient pas automatiquement les privilèges `is_staff` ou `is_superuser` |
| TS-22 | Commande de superutilisateur | `createsuperuser` crée un compte compatible avec `accounts.User` et un mot de passe haché |

Les comptes et mots de passe utilisés par ces tests sont synthétiques et isolés dans la base de tests Django. Aucun utilisateur réel ou secret de C-Tech n’est inséré dans l’environnement de développement ou le dépôt.

## Couverture ajoutée par T-004

| Référence | Scénario | Résultat attendu |
|---|---|---|
| TS-23 | Référentiel Service | Création, unicité du nom, état actif et timestamps vérifiés |
| TS-24 | Référentiels Category et DocumentType | Création et représentation textuelle vérifiées séparément |
| TS-25 | Création d’archive | Les relations métier, les valeurs par défaut et le Custom User sont correctement persistés |
| TS-26 | Référence d’archive | Une seconde archive ne peut pas réutiliser une référence existante |
| TS-27 | Conservation des relations | La suppression d’un service, d’une catégorie ou d’un type référencé déclenche `ProtectedError` |
| TS-28 | Statut et confidentialité | `full_clean()` et les contraintes PostgreSQL refusent les valeurs non prévues |
| TS-29 | Intégrité de taille et checksum | Les tailles négatives et checksum non conformes sont refusés par validation et base de données |
| TS-30 | Dates et représentation | Les timestamps sont produits ; `document_date`, `archived_at` et `__str__` sont vérifiés |

Ces tests distinguent volontairement la validation applicative lancée par `full_clean()` des contraintes PostgreSQL appliquées lors de l’écriture. Les deux niveaux sont nécessaires car l’appel standard à `save()` ne lance pas automatiquement `full_clean()`.
