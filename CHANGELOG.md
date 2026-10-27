# Journal des modifications

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; les versions suivent le versionnage sémantique.

## [2.1.0] — 2026-10-27 · Feuille de route livrée

Quatre des six améliorations soumises au vote des utilisateurs sont livrées ; elles apparaissent comme « Disponible » dans la page Futures améliorations.

### Recherche enrichie

- Extraction du texte des PDF (pypdf), DOCX, XLSX et TXT au dépôt, bornée en taille, en pages et en caractères ; un document illisible reste archivable.
- Index PostgreSQL pondéré (référence et titre, puis description et classement, puis contenu), configuration `french`, insensible aux accents ; syntaxe « websearch » (guillemets, exclusion `-`).
- Tri par pertinence par défaut lors d’une recherche, extraits surlignés et échappés, palette de commandes branchée sur le même moteur.
- Commande `reindex_archives` (`--missing` au démarrage Render).

### Calendrier de conservation

- Dates de prochaine révision et de fin de conservation, contrôles de cohérence, durées usuelles (+1, +5, +10, +30 ans).
- Filtre « Échéance de conservation », tri par fin de conservation, section « E. Conservation » sur la fiche avec frise d’avancement.
- Carte « Échéances de conservation » sur le tableau de bord, limitée au périmètre visible.

### Indicateurs et rapports

- Rapport d’activité imprimable sur 30, 90 ou 365 jours, avec activité du journal pour les administrateurs.
- Export CSV des archives filtrées, journalisé (`ARCHIVE_EXPORT`), sans empreinte et protégé contre les formules.

### Sécurité renforcée

- Double authentification TOTP (RFC 6238, sans dépendance), QR code (`segno`), anti-rejeu, huit codes de secours stockés sous forme d’empreintes et affichés une seule fois.
- Connexion en deux étapes : le mot de passe seul n’ouvre plus de session, l’étape expire en 5 minutes et les codes erronés sont limités et audités.
- Revue des droits pour les administrateurs : comptes privilégiés sans second facteur, comptes inactifs depuis 90 jours.

## [2.0.0] — 2026-10-27

### Interface « Sceau » (refonte complète)

- Nouveau système de design : jetons de couleur, thèmes clair, sombre et système (mémorisé), typographies Fraunces, Geist et Geist Mono auto-hébergées (OFL), sprite d’icônes SVG interne, animations sobres respectant `prefers-reduced-motion`, styles d’impression.
- Sceau génératif : chaque archive reçoit un emblème unique dérivé de sa référence (jamais de l’empreinte du fichier), rendu côté serveur et reproduit à l’identique en JavaScript pour l’aperçu du formulaire.
- Coquille applicative : barre latérale réductible avec carte d’habilitation (niveaux accessibles et verrouillés), tiroir mobile, barre supérieure vitrée, menu de compte, notifications animées à fermeture automatique.
- Palette de commandes (<kbd>Ctrl</kbd>/<kbd>⌘</kbd> <kbd>K</kbd>) : navigation, actions et recherche d’archives en direct, entrées filtrées par rôle côté serveur.
- Raccourcis clavier : <kbd>/</kbd> recherche, <kbd>G</kbd> puis <kbd>D</kbd>/<kbd>A</kbd>/<kbd>J</kbd>/<kbd>P</kbd>, <kbd>N</kbd> nouvelle archive, <kbd>T</kbd> thème, <kbd>?</kbd> aide.
- Tableau de bord : bandeau d’accueil avec anneau de couverture SHA-256, six indicateurs avec mini-courbe, flux d’archivage sur douze mois, anneau de confidentialité, couverture d’intégrité et alertes sur 30 jours, classement des services. Pour les administrateurs : pouls du journal sur 26 semaines et actions les plus fréquentes. Tous les graphiques sont des SVG calculés côté serveur sur le seul périmètre visible.
- Archives : recherche large, filtres avancés repliables, pastilles de filtres actifs retirables, tri sur liste blanche, vue tableau ou grille, barre de périmètre proportionnelle, pagination numérotée.
- Fiche d’archive : en-tête avec sceau, copie de la référence, panneau d’intégrité visuel (conforme, alerte, jamais revérifiée, sans empreinte), aperçu à la demande des images et textes, historique des accès réservé aux administrateurs, cycle de vie pour les autres rôles, impression.
- Formulaire : sceau en direct, étapes suivies au défilement, choix du statut et de la confidentialité en cartes (« qui pourra voir ce document »), dépôt par glisser-déposer avec contrôle anticipé de format et de taille.
- Journal d’audit : chronologie groupée par jour, indicateurs, filtres par période.
- Connexion et inscription : mise en page scindée avec coffre animé, affichage du mot de passe, jauge de robustesse indicative.
- Profil : carte d’identité, statistiques personnelles, habilitation, choix du thème.

### Ajouts fonctionnels

- Aperçu des images PNG/JPEG et des textes (64 Ko au plus), signature revérifiée à la lecture, réponse isolée (`sandbox`, `nosniff`, `no-store`), événement d’audit `ARCHIVE_PREVIEW`.
- Export CSV du journal filtré, protégé contre l’injection de formules, lui-même audité (`AUDIT_EXPORT`).
- Changement de mot de passe en libre-service, audité (`PASSWORD_CHANGE`).
- Retrait de la photo de profil.
- Commande `seed_demo` : jeu de démonstration idempotent et cohérent avec le RBAC, refusé en production.
- Sonde `/healthz/` (base de données), exemptée de la redirection HTTPS.

### Sécurité

- Content-Security-Policy stricte sans `unsafe-inline` (assouplie pour les seuls styles de l’admin Django) et Permissions-Policy.
- Verrouillage temporaire d’un compte après des échecs de connexion répétés ; mot de passe non testé pendant le verrouillage ; clés de cache hachées.
- Limitation des inscriptions par origine.
- `bootstrap_default_admins --create-only` au démarrage : un administrateur désactivé n’est plus réactivé et un mot de passe n’est plus réinitialisé à chaque redémarrage ; mots de passe faibles refusés ; `CTECH_BOOTSTRAP_RECONCILE` pour réaligner explicitement.
- Fichier, taille et empreinte en lecture seule dans l’admin Django : ils ne passent que par le formulaire validé et audité.
- Suppression du fichier stocké si la création d’archive échoue (plus de fichiers orphelins).
- Session de 8 heures par défaut.
- Django 5.2 LTS (5.1 n’est plus maintenu) et Pillow 13 : `pip-audit` ne signale plus aucune vulnérabilité connue (80 avant).

### Exploitation

- `STORAGES` configuré : les statiques de production sont enfin hachés et compressés (l’ancien `STATICFILES_STORAGE` était ignoré par Django 5.1).
- `LOGGING` sur la console : les erreurs 500 et les événements de sécurité apparaissent dans les journaux Render.
- Cache base de données partagé entre workers en production (`createcachetable` au démarrage).
- CI GitHub Actions : PostgreSQL 17, Python 3.12 et 3.13, contrôles de déploiement, build des statiques, tests, `pip-audit`.
- `constraints.txt` (versions figées), `.gitattributes` (LF), `compose.yaml`, `Makefile`.
- Fuseau d’affichage Europe/Paris.
- Hachage MD5 pendant les seuls tests : la suite passe de ~104 s à ~13 s.
- Index du journal d’audit sur l’horodatage et sur l’action.
- Liste des archives : un agrégat unique remplace quatre requêtes de comptage.
- Avatar différé au chargement de session : il n’est plus lu à chaque requête.

### Supprimé

- Vue et gabarit `accounts/home` inutilisés.

## [1.1.0]

- Inscription par e-mail (rôle Consultant), connexion par e-mail, guide d’accueil, feuille de route participative avec votes, avatar privé.

## [1.0.0]

- MVP académique : rôles, RBAC par confidentialité, archives, stockage privé, intégrité SHA-256, journal d’audit, tableau de bord.
