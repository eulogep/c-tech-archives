# Journal des décisions techniques

Ce document consigne les choix structurants du projet afin qu’ils puissent être justifiés dans le mémoire et revus lorsque de nouvelles informations seront fournies par C-Tech.

## ADR-001 — Monolithe modulaire Django

**Décision.** Le MVP utilisera un monolithe Django organisé en applications fonctionnelles (`accounts`, `archives`, `audit`, `dashboard`).

**Justification.** Cette structure est suffisamment modulaire pour séparer les responsabilités tout en étant simple à déployer, à tester et à expliquer dans un cadre académique. Elle évite la surcharge d’exploitation d’un système distribué.

**Alternative étudiée.** Frontend React séparé ou microservices.

**Pourquoi elle n’est pas retenue.** Ces options ajoutent des API, un second cycle de développement frontend et une complexité de déploiement qui ne sont pas nécessaires au MVP.

## ADR-002 — PostgreSQL comme base relationnelle cible

**Décision.** PostgreSQL sera utilisé en environnement de développement intégré et de production cible.

**Justification.** Le modèle contient des entités liées, des contraintes d’unicité, des recherches et un journal d’audit. Une base relationnelle répond directement à ces besoins et PostgreSQL est adapté à l’évolution contrôlée de requêtes et d’index.

**Alternative étudiée.** SQLite uniquement.

**Pourquoi elle n’est pas retenue.** SQLite peut faciliter certains démarrages locaux mais ne représente pas la cible relationnelle multi-utilisateur retenue pour le projet.

## ADR-003 — Modèle utilisateur Django personnalisé

**Décision.** Un modèle `User` personnalisé sera défini avant la première migration métier, à partir de `AbstractUser`.

**Justification.** Les rôles demandés et l’unicité de l’email font partie du besoin. La création précoce évite une migration complexe ultérieure depuis le modèle utilisateur Django par défaut.

**Alternative étudiée.** Utiliser le modèle Django par défaut avec un profil séparé.

**Pourquoi elle n’est pas retenue.** Cette option répartit les informations centrales de l’utilisateur et complique la gestion explicite des rôles.

## ADR-004 — Stockage privé et téléchargement contrôlé

**Décision.** Les fichiers d’archive seront stockés hors exposition publique et servis via une vue qui vérifie les autorisations.

**Justification.** La confidentialité ne peut pas reposer sur une URL difficile à deviner. Le contrôle applicatif est nécessaire avant toute diffusion du contenu.

**Alternative étudiée.** Exposer directement le répertoire média avec une URL publique.

**Pourquoi elle n’est pas retenue.** Cette alternative permettrait un accès direct si l’URL est connue ou devinée.

## ADR-005 — Empreinte SHA-256 pour l’intégrité

**Décision.** Une empreinte SHA-256 sera calculée à la réception du fichier et conservée avec l’archive.

**Justification.** La comparaison d’une empreinte recalculée avec la valeur enregistrée permet de détecter une altération du fichier. La solution est compréhensible et testable dans le périmètre du MVP.

**Alternative étudiée.** Signature électronique ou blockchain.

**Pourquoi elle n’est pas retenue.** Ces mécanismes répondent à des objectifs plus larges de preuve, d’identité ou de non-répudiation, hors du périmètre initial.

## ADR-006 — Audit applicatif dédié

**Décision.** Les opérations sensibles seront enregistrées dans le modèle `AuditLog` de l’application `audit`.

**Justification.** Un journal métier permet de lier l’action, l’utilisateur, l’archive, la date, l’adresse IP et un détail contrôlé, puis de l’exposer à l’administrateur.

**Alternative étudiée.** Se contenter des journaux techniques du serveur.

**Pourquoi elle n’est pas retenue.** Les journaux techniques ne fournissent pas nécessairement une traçabilité métier structurée, recherchable et liée aux entités de l’application.

## ADR-007 — Modèle utilisateur personnalisé dès le démarrage

**Décision.** Le projet utilise `accounts.User`, un modèle personnalisé basé sur `AbstractUser`, déclaré par `AUTH_USER_MODEL = "accounts.User"` avant toute migration métier.

**Justification.** Les rôles métier font partie du besoin initial. Définir le modèle dès le début évite une migration risquée depuis `auth.User` lorsque les archives et journaux d’audit dépendront des utilisateurs. `AbstractUser` conserve le hachage des mots de passe, les permissions, les groupes, les sessions et l’administration native de Django.

**Alternative étudiée.** Conserver le modèle `auth.User` par défaut et créer un profil séparé.

**Pourquoi elle n’est pas retenue.** Cette alternative séparerait les informations d’identité et de rôle, introduirait une relation additionnelle et rendrait l’évolution des relations métier moins directe.

## ADR-008 — Username comme identifiant technique du MVP

**Décision.** Le champ `username` d’`AbstractUser` reste l’identifiant technique de connexion. L’email est obligatoire et unique, mais il n’est pas encore le champ `USERNAME_FIELD`.

**Justification.** Cette solution utilise le flux Django standard sans réécrire les mécanismes d’authentification, ce qui réduit le risque et reste facile à expliquer et tester dans le cadre du MVP. L’unicité de l’email préserve une évolution future si C-Tech décide d’une connexion par email.

**Alternative étudiée.** Utiliser immédiatement l’email comme identifiant principal.

**Pourquoi elle n’est pas retenue.** Ce choix impliquerait une personnalisation plus profonde des formulaires, des commandes et des parcours d’authentification, alors qu’aucune exigence C-Tech ne le justifie encore.

## ADR-009 — Rôle métier distinct des permissions et du superutilisateur

**Décision.** `User.role` exprime le rôle métier principal (`ADMINISTRATEUR`, `AGENT_ARCHIVES`, `CONSULTANT`), tandis que les droits précis resteront attribuables avec les permissions et groupes Django. Le rôle `ADMINISTRATEUR` ne modifie ni `is_staff` ni `is_superuser`.

**Justification.** L’authentification établit l’identité de l’utilisateur ; l’autorisation détermine les actions qu’il peut réaliser. Un rôle métier facilite les règles de haut niveau, tandis que les groupes et permissions permettent un contrôle serveur fin et réutilisable. Un superutilisateur Django détient des privilèges techniques globaux et ne doit pas être créé implicitement par un rôle fonctionnel.

**Conséquence.** Tous les futurs modèles qui ciblent un utilisateur doivent utiliser `settings.AUTH_USER_MODEL` ou `get_user_model()` selon leur contexte. Les imports directs de `django.contrib.auth.models.User` sont interdits dans le code métier.
