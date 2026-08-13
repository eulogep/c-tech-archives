# Sécurité du MVP

## Principe de vérifiabilité

Le caractère « sécurisé » fait partie du sujet académique. Chaque mécanisme annoncé doit donc être implémenté, testé et traçable dans le code ; toute mesure non implémentée doit être présentée comme une perspective. La sécurité est contrôlée côté serveur et ne repose jamais exclusivement sur l’interface utilisateur.

## Mesures requises

| Domaine | Mesure attendue | Ticket cible | Preuve attendue |
|---|---|---|---|
| Authentification | Authentification Django, mots de passe hachés, session gérée par le framework | T-006 | Tests de connexion valide et invalide |
| Autorisation | Permissions et vérifications dans les vues/services | T-011 | Tests d’accès refusé par rôle |
| CSRF | Jetons CSRF dans les formulaires mutables | T-006/T-008 | Inspection des formulaires et tests Django |
| SQL | ORM Django et absence de concaténation SQL dynamique | T-004 à T-009 | Revue de code |
| XSS | Échappement automatique des templates et prudence avec `safe` | T-008/T-015 | Revue de templates et tests de rendu |
| Secrets | Variables d’environnement, `.env` ignoré, `.env.example` sans secret | T-001/T-002 | Revue Git |
| Upload | Validation de taille, extension, nom et MIME si disponible | T-010 | Tests de fichiers acceptés/refusés |
| Fichiers | Stockage privé et téléchargement par vue protégée | T-010/T-011 | Test d’URL devinée et refus d’accès |
| Intégrité | Empreinte SHA-256 à l’enregistrement et vérification ultérieure | T-013 | Tests checksum identique/modifiée |
| Audit | Journalisation d’opérations sensibles avec IP et date | T-012 | Tests d’événements produits |

## Politique de contrôle d’accès initiale

| Action | Administrateur | Agent d’archives | Consultant |
|---|---:|---:|---:|
| Gérer les utilisateurs et référentiels | Oui | Non | Non |
| Créer une archive | Oui | Oui | Non |
| Rechercher et consulter | Oui | Oui | Seulement si autorisé |
| Modifier une archive | Oui | Métadonnées autorisées | Non |
| Télécharger | Oui | Oui | Seulement si autorisé |
| Supprimer / désactiver | Oui | Non | Non |
| Consulter l’audit | Oui | Non | Non |

Les règles « seulement si autorisé » supposent une politique de confidentialité. Avant d’implémenter une ACL fine, le MVP devra définir avec C-Tech si l’autorisation dépend du rôle, du service, de la confidentialité ou d’une attribution nominative. L’implémentation initiale ne devra jamais prétendre à une granularité qui n’a pas été décidée.

## Fichiers et téléchargements

Les fichiers sont un actif sensible. En production, leur chemin ne doit pas être accessible publiquement. La vue de téléchargement doit : identifier l’archive par son identifiant ou sa référence, vérifier l’authentification et l’autorisation, inscrire l’événement d’audit, puis diffuser le fichier à l’utilisateur autorisé. L’utilisation d’un serveur web avec mécanisme interne de diffusion pourra être étudiée lors du déploiement ; elle ne remplace pas le contrôle applicatif.

Les contrôles de type MIME améliorent la détection mais ne constituent pas une garantie absolue. Le système combinera une liste d’extensions autorisées, un plafond de taille configurable, la normalisation du nom de fichier et, si disponible, une vérification de type. Les fichiers exécutables et les extensions non autorisées seront refusés.

## Paramètres à ne jamais versionner

Le fichier `.env` contiendra notamment `SECRET_KEY`, les paramètres de connexion PostgreSQL et les paramètres propres à l’environnement. Il restera ignoré par Git. Seul `.env.example` sera commité avec des valeurs de démonstration non sensibles.

## Limites et perspectives

Le MVP n’inclut pas le chiffrement au repos, l’antivirus, la signature électronique, le DLP, l’authentification multifacteur ou une gestion documentaire réglementaire complète. Ces sujets pourront être étudiés comme perspectives après une analyse des risques, des contraintes légales applicables et des besoins réels de C-Tech.
