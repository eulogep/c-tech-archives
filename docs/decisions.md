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

## ADR-010 — Référentiels séparés et relations protégées pour les archives

**Décision.** Les entités `Service`, `Category` et `DocumentType` sont des référentiels indépendants reliés à `Archive` par des clés étrangères `PROTECT`. Elles comportent un indicateur `is_active` au lieu d’être supprimées lorsqu’elles deviennent obsolètes.

**Justification.** Une archive doit conserver son contexte organisationnel et documentaire. `PROTECT` évite qu’une suppression de référentiel ou d’utilisateur ne supprime un ensemble d’archives ou ne retire leur rattachement historique. Les noms uniques évitent des référentiels ambigus dans le MVP.

**Alternative étudiée.** Suppression en cascade, relations nulles ou hiérarchie récursive de catégories.

**Pourquoi elle n’est pas retenue.** La cascade risquerait de détruire l’historique, `SET_NULL` le rendrait incomplet et une hiérarchie ajouterait une complexité non validée par C-Tech.

## ADR-011 — Métadonnées d’archive sans upload dans T-004

**Décision.** `Archive` conserve la référence unique, les relations métier, les dates, le statut, la confidentialité, la taille et le checksum, mais ne contient pas encore de champ de fichier ni de logique d’upload.

**Justification.** Le ticket est limité à la modélisation et à l’intégrité de la base. Ajouter un stockage de fichier, une validation MIME, une empreinte automatique ou un téléchargement sécurisé créerait des comportements de sécurité qui doivent être traités et testés dans un ticket dédié.

**Conséquence.** `checksum` est accepté uniquement vide ou au format SHA-256, et `file_size` est exprimé en octets avec une valeur non négative. Ces champs préparent l’intégrité future sans prétendre assurer le stockage sécurisé dès T-004.

## ADR-012 — Authentification native Django par session

**Décision.** Le MVP utilise l’authentification native Django par session, avec `LoginView`, `LogoutView`, `AuthenticationForm`, `@login_required` et les cookies de session protégés configurés au ticket T-002.

**Justification.** La plateforme est rendue côté serveur avec Django Templates. Les sessions Django s’intègrent directement au modèle utilisateur personnalisé, aux protections CSRF, aux mécanismes de hachage et aux vues génériques du framework. Cette solution est éprouvée, réduite et facilement démontrable pour le MVP.

**Alternative étudiée.** JWT ou un système d’authentification personnalisé.

**Pourquoi elle n’est pas retenue.** JWT répond davantage aux API sans état ou à des clients séparés et ajouterait une gestion de token inutile à cette architecture. Un système personnalisé risquerait de réimplémenter de manière moins sûre le hachage, les sessions ou les contrôles de redirection déjà fournis par Django.

## ADR-013 — Deny-by-default avant RBAC métier

**Décision.** Jusqu’au ticket T-011, l’espace de gestion des métadonnées d’archives est limité aux comptes techniques `is_staff` ou `is_superuser` par un `StaffRequiredMixin` centralisé.

**Justification.** Les rôles métier existent dans le modèle utilisateur mais les règles d’autorisation par action, archive et niveau de confidentialité ne sont pas encore validées. Ouvrir l’espace CRUD à tous les comptes authentifiés, ou assimiler le rôle `ADMINISTRATEUR` à `is_staff`, créerait une politique partielle, incohérente et difficile à remplacer. Une restriction temporaire explicite limite l’exposition jusqu’à ce que le RBAC final soit défini.

**Conséquence.** Les utilisateurs métier non staff reçoivent un refus HTTP 403 malgré leur authentification. Cette limitation est documentée et doit être remplacée, non étendue, au ticket T-011.


## ADR-014 — Recherche ORM simple avant moteur de recherche avancé

**Décision.** T-009 met en œuvre une recherche GET fondée sur l’ORM Django : correspondance insensible à la casse sur la référence, le titre et la description, complétée par des filtres combinables de référentiel, de statut, de confidentialité et de date. La vue conserve une pagination de vingt résultats et un ordre déterministe `-created_at`, `-pk`.

**Justification.** Les besoins actuellement validés portent sur une consultation interne de métadonnées structurées. Des `QuerySet` lisibles, paramétrés par Django et couverts par des tests fournissent une solution proportionnée, maintenable et adaptée au MVP. La persistance de la query string entre les pages rend les recherches reproductibles sans ajouter de composant externe.

**Alternative étudiée.** PostgreSQL Full Text Search avec `tsvector`, Elasticsearch, embeddings ou recherche sémantique.

**Pourquoi elle n’est pas retenue.** Aucun volume, exigence de pertinence, besoin linguistique ou contrainte de recherche non structurée n’a été validé pour justifier ces technologies. Elles exigeraient des index, un paramétrage, une stratégie de synchronisation et des tests d’exploitation supplémentaires. Elles restent des évolutions possibles après mesure des besoins réels, sans être anticipées dans le modèle ni dans les migrations de T-009.

**Conséquence.** La recherche textuelle reste volontairement simple et ne prétend pas offrir un classement par pertinence. Les règles RBAC de confidentialité ne sont pas introduites : le filtre de confidentialité s’applique uniquement aux archives déjà accessibles via la garde technique temporaire `StaffRequiredMixin`.


## ADR-015 — Stockage privé des fichiers avec accès applicatif contrôlé

**Décision.** Le contenu des archives est conservé hors exposition publique dans un `FileField` Django utilisant `PrivateArchiveStorage`, configuré par `PRIVATE_MEDIA_ROOT`. PostgreSQL conserve les métadonnées et le chemin relatif généré ; la diffusion passe exclusivement par une vue Django protégée qui retourne `FileResponse` en pièce jointe.

**Justification.** Connaître ou deviner une URL ne doit pas permettre de contourner une autorisation documentaire. Un nom physique généré avec UUID évite les collisions, supprime toute dépendance au chemin fourni par le client et maintient une séparation claire entre les données relationnelles et le contenu binaire. L’abstraction Django Storage permet de remplacer le backend local du MVP par un stockage objet privé ou réseau sans modifier le modèle métier.

**Alternative étudiée.** Exposer les fichiers par `MEDIA_URL` et construire des liens directs avec `archive.file.url`.

**Pourquoi elle n’est pas retenue.** Cette alternative transformerait le chemin de stockage en mécanisme d’accès. Une URL connue, partagée ou devinée pourrait contourner les contrôles applicatifs. Elle rendrait également plus difficile l’application future des règles RBAC, de confidentialité et d’audit.

**Conséquence.** Le téléchargement est disponible uniquement par `/archives/<pk>/download/` après la garde temporaire `StaffRequiredMixin`. Le remplacement de fichier n’est pas permis dans l’édition de métadonnées ; il attend une politique de versioning et de conservation validée avec C-Tech. Les validations de taille et de format réduisent le risque, sans être présentées comme une protection antivirus.


## ADR-016 — Autorisation centralisée et filtrage au niveau QuerySet

**Décision.** La politique RBAC provisoire des archives est définie dans `archives.permissions`. Les fonctions de cette couche déterminent les niveaux de confidentialité visibles, les actions de création et de modification, puis filtrent les QuerySets avec `visible_archives_for` avant toute liste, recherche, pagination, vue objet ou agrégation de dashboard.

**Justification.** Une source de vérité unique évite les divergences entre la liste, le détail, la recherche, le téléchargement et les formulaires. Filtrer au niveau QuerySet constitue une défense en profondeur : les archives hors périmètre ne sont pas retournées, comptées ou proposées comme référentiels, ce qui réduit les fuites par inférence. Les contrôles objet complètent le filtrage pour les URLs saisies directement.

**Politique de réponse.** Une archive existante mais hors périmètre retourne HTTP 404 afin de ne pas révéler son existence. Une action interdite sur une archive déjà visible retourne HTTP 403. Les formulaires limitent les choix puis valident de nouveau les données soumises, afin d’empêcher une escalade de confidentialité par POST falsifié.

**Alternative étudiée.** Conserver `StaffRequiredMixin`, ou disperser des conditions `if user.role == ...` dans chaque vue et chaque gabarit.

**Pourquoi elle n’est pas retenue.** Le statut staff est un privilège technique, pas une politique métier de confidentialité. Les conditions dispersées sont difficiles à auditer, risquent de produire des règles incohérentes et ne garantissent pas le filtrage des recherches, compteurs et téléchargements.

**Conséquence.** La matrice Administrateur / Agent / Consultant est centralisée mais demeure provisoire. Elle n’ajoute aucune ACL de service, partage nominatif, audit ou versioning ; ces exigences devront être confirmées avec C-Tech et traitées dans les tickets appropriés.


## ADR-017 — Audit métier explicite et append-only

**Décision.** Les opérations métier sensibles sont enregistrées dans le modèle transverse `AuditLog` par le service central `record_audit_event`. Les événements d’authentification utilisent les signaux Django ; les actions d’archive sont intégrées explicitement dans les vues après réussite et contrôles RBAC. Le journal est append-only au niveau applicatif, et son administration Django est en lecture seule.

**Justification.** Un modèle structuré permet de répondre de manière cohérente à « qui a fait quoi, sur quelle archive, quand et depuis quelle IP si disponible ». Une API d’écriture unique évite les structures divergentes dans les vues. Les actions d’archive ne reposent pas sur `post_save`, car ce signal ne permettrait pas de distinguer proprement une action web, un import, une opération d’administration ou une création technique.

**Données minimales.** Le journal garde l’acteur, son identifiant lisible, l’action, l’archive et sa référence, l’horodatage serveur, l’IP nullable et des détails limités à `source` ou `changed_fields`. Il ne stocke aucun mot de passe, hash, session, formulaire POST intégral, contenu de fichier ou chemin privé. `REMOTE_ADDR` est retenu ; `X-Forwarded-For` est ignoré sans proxy de confiance documenté.

**Cohérence et échec.** Les écritures de création et modification d’archive sont réalisées dans la même transaction que l’événement d’audit. Une erreur de journalisation est propagée : l’application ne doit pas prétendre qu’une opération sensible a été tracée lorsque ce n’est pas le cas. Les vues de consultation et téléchargement ne journalisent qu’après accès autorisé et ressource disponible.

**Alternative étudiée.** Journaliser tous les GET, utiliser un `post_save` général ou mélanger les événements métier avec les logs techniques du serveur.

**Pourquoi elle n’est pas retenue.** Ces alternatives génèrent du bruit, ne possèdent pas assez de contexte métier ou risquent de collecter des données sensibles. L’append-only applicatif ne prétend pas assurer une immutabilité absolue : un SIEM, une externalisation ou une chaîne cryptographique sont des évolutions de production hors périmètre.


## ADR-018 — SHA-256 comme empreinte de référence d’intégrité

**Décision.** Le champ `Archive.checksum` existant devient la référence SHA-256 de l’intégrité du fichier. L’empreinte est calculée par le module central `archives.integrity` après stockage du fichier lors de la création, à l’aide de `hashlib.sha256()` et de blocs de 64 KiB. Aucune valeur client ne peut la définir. La vérification est explicite, via POST avec CSRF, et renvoie un état non ambigu sans modifier la référence historique.

**Justification.** SHA-256 est un algorithme standard disponible dans la bibliothèque Python. Une empreinte déterministe permet de comparer le contenu actuel au contenu enregistré lors du dépôt. Lire par blocs limite la mémoire supplémentaire utilisée, alors que le coût I/O de la vérification demeure proportionnel à la taille du fichier.

**États et audit.** Le service distingue `VALID`, `MISMATCH`, `NO_FILE`, `MISSING_CHECKSUM`, `FILE_MISSING` et `ERROR`. `MISMATCH` ne réécrit jamais le checksum. Chaque vérification autorisée est journalisée par `ARCHIVE_INTEGRITY_CHECK` avec le seul résultat ; les hashes complets ne sont pas dupliqués dans l’audit.

**Alternative étudiée.** Recalculer à chaque téléchargement ou consultation, créer un nouveau champ checksum, ou considérer SHA-256 comme un mécanisme de sécurité complet.

**Pourquoi elle n’est pas retenue.** Le recalcul automatique imposerait un coût I/O inutile sur les parcours courants. Le champ existant respecte déjà le format requis, donc une migration du domaine archive serait sans justification. SHA-256 mesure l’intégrité mais n’est ni du chiffrement, ni une signature numérique, ni une défense contre une compromission simultanée du stockage et de la base. La vérification reste soumise à un risque TOCTOU hors périmètre MVP.


## ADR-019 — Durcissement fondé sur des tests transverses et classification explicite des limites

**Décision.** T-014 ajoute une revue transverse et la matrice `HARD-001` à `HARD-025` sans introduire de nouvelle fonctionnalité de sécurité disproportionnée. Les faiblesses doivent être reproduites par test avant correction. En l’absence de vulnérabilité significative reproductible, le ticket documente les contrôles existants, les résultats de `check --deploy` et les risques résiduels au lieu de déclarer artificiellement une faille critique.

**Justification.** Le MVP possède déjà des contrôles distribués entre authentification, RBAC, formulaires, stockage privé, audit et intégrité. Les tests transverses vérifient leur cohérence au niveau des routes et de la configuration, notamment les scénarios IDOR, CSRF et mass assignment que des tests unitaires isolés peuvent manquer.

**Déploiement.** Les warnings `check --deploy` observés en développement ne sont pas désactivés, car le développement local est volontairement HTTP avec DEBUG. La production doit fournir son secret, ses hôtes, HTTPS, cookies secure, redirection SSL et HSTS par environnement. Le preload HSTS reste une décision explicite après validation du domaine complet.

**Limites.** T-014 ne prétend pas certifier OWASP, fournir un pentest externe, installer un rate limiter, un antivirus, une signature numérique, une immutabilité WORM ou un scanner de dépendances. Ces éléments sont recensés comme prérequis ou risques résiduels pour la production.


## ADR-020 — Interface Django responsive, sans couche frontend additionnelle

**Décision.** T-015 adopte une feuille de style centralisée et des gabarits Django réutilisables pour fournir une interface responsive et accessible au niveau d’une revue légère. Aucun framework JavaScript, build tooling, CDN critique, modèle, migration ou endpoint backend supplémentaire n’est ajouté.

**Justification.** Le MVP est déjà rendu côté serveur et ses parcours sont principalement documentaires : connexion, recherche, lecture de métadonnées, formulaire, téléchargement contrôlé, intégrité et audit. Une couche frontend distincte augmenterait la surface technique sans répondre à une exigence validée. Des composants CSS partagés, des structures HTML sémantiques et des gabarits cohérents améliorent l’expérience et restent simples à expliquer pendant la soutenance.

**Sécurité.** La visibilité des entrées de navigation réutilise les indicateurs `archive_policy` et `audit_policy` existants. Cette ergonomie ne constitue pas un contrôle d’accès : les politiques RBAC, QuerySets, mixins, vues, méthodes HTTP, CSRF, audit et stockage privé restent les autorités serveur.

**Alternative étudiée.** Introduire React, Vue, un framework CSS externe, un CDN ou du JavaScript applicatif pour la sidebar et les formulaires.

**Pourquoi elle n’est pas retenue.** Ces alternatives créeraient des dépendances, des mécanismes de build et une complexité d’intégration disproportionnés. Elles pourraient également détacher l’interface des protections Django déjà vérifiées. Le T-015 privilégie une application server-rendered fonctionnelle sans JavaScript pour ses parcours principaux.
