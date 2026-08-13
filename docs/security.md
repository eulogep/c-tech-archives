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

## Fondations d’identité et d’autorisation — T-003

Le projet s’appuie sur `accounts.User`, déclaré comme `AUTH_USER_MODEL` avant la création des modèles métier. Django gère le hachage et la vérification des mots de passe ; aucune fonctionnalité du projet ne doit stocker ou comparer un mot de passe en clair. Les tests vérifient qu’un mot de passe créé par le gestionnaire Django est distinct de sa valeur source et qu’il reste vérifiable avec `check_password()`.

> **Authentification** : le système vérifie qui est l’utilisateur. **Autorisation** : le système vérifie que cet utilisateur dispose du droit d’effectuer une action donnée. Ces mécanismes sont complémentaires et les futures vues devront toujours vérifier les permissions côté serveur.

Le champ `role` contient le rôle métier principal et ses valeurs sont limitées à `ADMINISTRATEUR`, `AGENT_ARCHIVES` et `CONSULTANT` par les choix Django et une contrainte de base de données. Il ne remplace pas les groupes ni les permissions. En particulier, un Administrateur métier ne devient pas automatiquement un superutilisateur Django ou un membre du personnel d’administration. Les privilèges `is_staff` et `is_superuser` restent explicites, contrôlés et réservés aux besoins techniques.

Les futures clés étrangères vers l’utilisateur utiliseront `settings.AUTH_USER_MODEL`. Les règles de permissions fines, les décorateurs et les mixins seront mis en œuvre par les tickets fonctionnels concernés, notamment lors de la gestion des archives ; ils ne sont pas anticipés par des contrôles d’interface dans T-003.

## Intégrité du domaine documentaire — T-004

T-004 protège la cohérence des métadonnées avant tout stockage de fichier. La référence d’archive est unique, les tailles négatives sont interdites et les valeurs de statut ou de confidentialité sont limitées à des choix explicites à la fois dans Django et dans PostgreSQL. Les relations protégées empêchent la suppression accidentelle d’un service, d’une catégorie, d’un type documentaire ou d’un utilisateur lorsque des archives les référencent.

Le champ `checksum` accepte uniquement une valeur vide ou une chaîne SHA-256 hexadécimale de 64 caractères. Il ne calcule aucune empreinte dans ce ticket, ne chiffre aucun document et ne confère aucun droit d’accès. Le calcul d’empreinte, la validation MIME, le stockage privé et le téléchargement contrôlé sont reportés au ticket d’upload sécurisé.

Les niveaux de confidentialité sont des métadonnées provisoires. Aucune autorisation d’archive ne doit encore être déduite du champ `confidentiality_level` : les contrôles RBAC et les permissions serveur seront introduits par les tickets fonctionnels pertinents.

## Authentification par session Django — T-006

T-006 utilise `LoginView`, `LogoutView`, `AuthenticationForm`, `@login_required` et le moteur de sessions natif de Django. Cette approche s’intègre directement au modèle `accounts.User`, réutilise les mécanismes éprouvés de vérification de mot de passe et évite de stocker manuellement un identifiant, un rôle ou un mot de passe dans des cookies personnalisés.

> **Authentification** : le serveur vérifie l’identité présentée par un utilisateur. **Autorisation** : le serveur vérifie ensuite ce que cet utilisateur peut faire. T-006 couvre uniquement l’authentification ; les permissions métier sur les archives seront introduites dans le ticket T-011.

Le mot de passe n’est jamais lu depuis PostgreSQL ni comparé manuellement. Django conserve une **empreinte de hachage** non réversible, et vérifie la valeur saisie avec son mécanisme de hachage. Un hash n’est pas un chiffrement : il ne doit pas être déchiffré pour authentifier un utilisateur.

La page de connexion contient un jeton `{% csrf_token %}`. La protection CSRF empêche un site tiers de déclencher à l’insu d’un utilisateur authentifié une action utilisant sa session. La déconnexion est réalisée par un formulaire POST protégé CSRF, conformément au comportement moderne de Django, afin de ne pas être déclenchée par une simple ressource intégrable.

Après une connexion réussie, Django crée et renouvelle la session associée à l’utilisateur ; l’application ne forge ni ne fixe d’identifiant de session. Ce renouvellement réduit le risque de fixation de session. Après la déconnexion, la session est invalidée et l’accès à la page protégée redirige de nouveau vers la connexion.

Les utilisateurs `is_active=False` sont refusés par le backend Django standard. Les échecs liés à un mot de passe incorrect, un utilisateur inconnu ou un utilisateur inactif affichent le même message générique afin de ne pas aider à l’énumération des comptes. Le paramètre `next` est traité par les contrôles Django : une destination locale est acceptée, tandis qu’une URL externe arbitraire est neutralisée.
