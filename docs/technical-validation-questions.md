# Questions techniques à valider avec C-Tech

> **But du document.** Les choix ci-dessous ne sont pas des processus métier inventés : ils doivent être confirmés par C-Tech avant de figer la configuration de production, la politique de sécurité ou les modalités d’exploitation. Les choix de développement du MVP restent provisoires tant que ces réponses ne sont pas connues.

## 1. Hébergement, environnement et disponibilité

| Réf. | Question à valider | Décision technique impactée | Valeur provisoire pour le MVP |
|---|---|---|---|
| TV-01 | L’application sera-t-elle hébergée sur un serveur interne, un VPS, un cloud public ou un poste local de démonstration ? | Architecture de déploiement, réseau, sauvegardes et supervision | Exécution locale de développement seulement |
| TV-02 | Quel système d’exploitation et quels niveaux d’accès administrateur sont disponibles sur l’hébergement cible ? | Procédure d’installation, services et mises à jour de sécurité | Ubuntu/Linux à confirmer |
| TV-03 | Quel niveau de disponibilité est attendu et quelles fenêtres de maintenance sont acceptables ? | Sauvegardes, supervision et procédure de restauration | Non défini pour le MVP |
| TV-04 | Un nom de domaine ou sous-domaine est-il prévu pour la plateforme ? | `ALLOWED_HOSTS`, DNS, HTTPS et certificats | `localhost` en développement |
| TV-05 | Qui administrera l’infrastructure, les comptes applicatifs et les mises à jour après la démonstration ? | Gouvernance d’exploitation et séparation des responsabilités | Administrateur de projet à définir |

## 2. Base de données et sauvegardes

| Réf. | Question à valider | Décision technique impactée | Valeur provisoire pour le MVP |
|---|---|---|---|
| TV-06 | PostgreSQL est-il disponible ou peut-il être installé sur l’environnement cible ? | Choix et installation de la base de données | PostgreSQL retenu dans la conception |
| TV-07 | La base de données doit-elle être sur le même serveur que l’application ou sur une instance distincte ? | Réseau, pare-feu, comptes et latence | Même environnement en développement |
| TV-08 | Quelle politique de sauvegarde est exigée pour PostgreSQL : fréquence, rétention, chiffrement et responsable ? | Plan de sauvegarde/restauration | À définir avant production |
| TV-09 | Comment une restauration sera-t-elle testée et qui l’autorisera ? | Procédure de reprise et traçabilité | Hors MVP, à documenter avant déploiement |
| TV-10 | Des contraintes de localisation, de souveraineté ou de conservation des données s’appliquent-elles ? | Hébergement, sauvegardes et conservation | À préciser par C-Tech |

## 3. Fichiers, formats et volumétrie

| Réf. | Question à valider | Décision technique impactée | Valeur provisoire pour le MVP |
|---|---|---|---|
| TV-11 | Quels formats de fichiers sont strictement autorisés et lesquels sont interdits ? | Liste blanche des extensions et validation MIME | PDF, Office et images courantes à confirmer |
| TV-12 | Quelle taille maximale par fichier et quel volume global faut-il supporter ? | Limites d’upload, espace disque et quotas | 10 MiB par fichier, provisoire |
| TV-13 | Où doivent résider les fichiers : disque du serveur, NAS interne ou stockage objet ? | Adaptateur de stockage, sauvegarde et accès réseau | Stockage local privé en développement |
| TV-14 | Les documents doivent-ils être chiffrés au repos ? Si oui, qui détient les clés et quelle solution est approuvée ? | Chiffrement, gestion de clés et récupération | Hors MVP, à analyser avant production |
| TV-15 | Faut-il une analyse antivirus ou antimalware à l’upload ? | Chaîne de validation, infrastructure et politique de rejet | Non implémentée dans le MVP |
| TV-16 | Les fichiers originaux doivent-ils être conservés après désactivation ou suppression d’une archive ? | Suppression logique/physique, stockage et audit | Décision différée à T-008 |

## 4. Identité, accès et sécurité réseau

| Réf. | Question à valider | Décision technique impactée | Valeur provisoire pour le MVP |
|---|---|---|---|
| TV-17 | Les comptes seront-ils créés localement, synchronisés avec un annuaire (LDAP/Active Directory) ou fédérés par SSO ? | Architecture d’authentification et gestion des comptes | Comptes Django locaux |
| TV-18 | Une authentification multifacteur est-elle exigée pour les administrateurs ou tous les utilisateurs ? | Parcours de connexion et choix de fournisseur | Hors MVP, perspective explicite |
| TV-19 | Quelle politique de mot de passe s’applique : longueur, complexité, expiration, verrouillage et réinitialisation ? | Validateurs Django, flux de récupération et journalisation | Politique Django renforcée à définir |
| TV-20 | L’accès sera-t-il réservé à un réseau interne, VPN ou certaines adresses IP ? | Pare-feu, proxy et contrôle réseau | Accessible seulement en local durant le MVP |
| TV-21 | Quel mécanisme HTTPS est accepté et qui gérera les certificats TLS ? | Proxy inverse, cookies sécurisés et déploiement | HTTP local uniquement ; HTTPS requis en production |
| TV-22 | L’accès du Consultant dépend-il uniquement de son rôle, de son service ou d’autorisations nominatives par archive ? | Modèle d’autorisation, requêtes de filtrage et contrôle de téléchargement | À confirmer avant T-011 |

## 5. Journalisation, conformité et exploitation

| Réf. | Question à valider | Décision technique impactée | Valeur provisoire pour le MVP |
|---|---|---|---|
| TV-23 | Quelle durée de conservation est requise pour les journaux d’audit ? | Rétention, archivage et capacité de stockage | Conservation non limitée pour les données de démonstration |
| TV-24 | Quelles actions et quelles données doivent apparaître dans l’audit, sans exposer de données sensibles ? | Schéma `AuditLog`, masquage et interface d’audit | Actions MVP définies dans `docs/security.md` |
| TV-25 | Les journaux doivent-ils être exportés ou envoyés vers un outil externe ? | Format d’export, intégration et sécurité | Non prévu au MVP |
| TV-26 | Quels textes légaux, politiques internes ou exigences contractuelles encadrent les archives ? | Rétention, droit d’accès, information des utilisateurs et sécurité | À fournir par C-Tech |
| TV-27 | Quelle procédure doit s’appliquer en cas d’incident : perte de fichier, accès non autorisé, indisponibilité ? | Plan de réponse, escalade et sauvegardes | À définir avant production |

## 6. Déploiement et acceptation

| Réf. | Question à valider | Décision technique impactée | Valeur provisoire pour le MVP |
|---|---|---|---|
| TV-28 | Quels environnements sont nécessaires : développement, recette, préproduction, production ? | Variables d’environnement, CI/CD et séparation des données | Développement local uniquement |
| TV-29 | Qui valide fonctionnellement et techniquement une version avant mise en service ? | Processus Git, recette et responsabilités | Validation académique et C-Tech à définir |
| TV-30 | Quels jeux de données de démonstration sont acceptables et comment seront-ils anonymisés ? | Fixtures, tests et respect de la confidentialité | Données synthétiques uniquement |
| TV-31 | Une procédure de déploiement reproductible est-elle attendue dès le MVP ? | Documentation, scripts et choix d’outils | Documentée avant toute mise en production |

## Priorités avant les prochains tickets

Les réponses **TV-11**, **TV-12** et **TV-22** sont nécessaires avant de figer T-010 (téléversement sécurisé) et T-011 (contrôle d’accès). Les réponses **TV-17**, **TV-19** et **TV-21** sont nécessaires avant une mise en production, mais ne bloquent pas l’initialisation du projet ni l’implémentation locale de l’authentification Django. Les réponses **TV-01**, **TV-06**, **TV-08**, **TV-13**, **TV-23** et **TV-27** sont indispensables avant le déploiement réel.
