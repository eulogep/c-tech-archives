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
