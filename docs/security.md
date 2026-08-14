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

## Confidentialité du dashboard avant RBAC — correctif de revue T-007

> Le dashboard T-007 n’affiche volontairement aucune métadonnée d’archive individuelle avant l’implémentation de la politique d’autorisation T-011. Une archive confidentielle peut révéler des informations sensibles par son titre, sa référence, son service ou sa catégorie même lorsque son fichier n’est pas accessible.

À l’étape historique T-007, l’authentification par session prouvait uniquement l’identité et le dashboard ne retournait donc que des métriques agrégées globales. Dans l’état final, l’authentification et l’autorisation sont distinctes : les agrégats du dashboard proviennent du QuerySet déjà filtré par rôle et confidentialité. La politique demeure un MVP à valider avec C-Tech, sans ACL de service ou attribution nominative.

## Deny-by-default avant RBAC final — T-008

À l’étape historique T-008, une restriction technique conservatrice limitait les écrans de métadonnées aux comptes `is_staff=True` ou `is_superuser=True` avant la définition du RBAC. Dans l’état final, T-011 applique la politique métier centralisée : Administrateur pour tous les niveaux, Agent pour PUBLIC/INTERNAL et Consultant pour PUBLIC. La règle applicable est documentée dans [`final-rbac-matrix.md`](final-rbac-matrix.md).

Cette règle provisoire ne doit pas être utilisée comme référence actuelle. Elle a été remplacée par `archives.permissions`, dont les règles par rôle, action, archive et confidentialité sont appliquées côté serveur dans les QuerySets, mixins, vues et formulaires.

Les formulaires reposent sur une liste blanche explicite de champs. `uploaded_by` est imposé par le serveur à l’utilisateur de la requête pendant la création. Les champs `file_size`, `checksum`, `created_at` et `updated_at` ne sont jamais acceptés depuis le navigateur. Cette séparation protège contre le mass assignment et la manipulation de champs techniques. Les formulaires POST conservent la protection CSRF native et les métadonnées sont rendues par Django sans filtre `safe`.

> La suppression physique est volontairement reportée jusqu’à validation de la politique de conservation et des règles C-Tech. T-008 ne crée donc aucune route ni action appelant `archive.delete()`.


## Recherche de métadonnées — T-009

La recherche utilise exclusivement l’ORM Django. Les termes saisis sont transmis comme paramètres de requête aux filtres `icontains` et aux objets `Q`; aucune chaîne SQL n’est construite ni concaténée à partir d’une entrée navigateur. Une saisie de type injection, par exemple `' OR 1=1 --`, est donc interprétée comme un texte de recherche et ne doit jamais élargir le jeu de résultats. Le scénario SEARCH-020 couvre ce comportement.

Les critères sont soumis par GET, ce qui rend une recherche partageable et compatible avec la pagination sans déclencher de mutation serveur. Les formulaires de création et de modification restent en POST avec protection CSRF. L’intervalle de dates est validé côté serveur : une date de début postérieure à la date de fin produit une erreur de formulaire et aucune liste de résultats. Les archives sans `document_date` ne provoquent pas d’exception et ne sont pas retenues lorsqu’un filtre de date est appliqué.

Le gabarit repose sur l’échappement automatique de Django et ne marque aucun terme de recherche comme sûr. Une valeur telle que `<script>alert(1)</script>` reste encodée dans le HTML, ce que couvre SEARCH-021. Les résultats ne rendent pas `checksum`, le hash du mot de passe de l’utilisateur ni les champs techniques de stockage. SEARCH-022 vérifie cette absence de divulgation.

La recherche conserve la garde temporaire deny-by-default de T-008 : anonyme vers la connexion et compte authentifié non staff vers HTTP 403. Le filtre `confidentiality_level` restreint uniquement les métadonnées déjà accessibles à ce garde technique ; il ne constitue pas une autorisation fondée sur la confidentialité. Les permissions métier détaillées seront définies et appliquées lors de T-011.


## Téléversement et téléchargement privés — T-010

Les fichiers sont écrits dans `PRIVATE_MEDIA_ROOT`, répertoire ignoré par Git et distinct de `MEDIA_URL`. Le chemin physique est généré côté serveur à partir d’un UUID et d’une extension contrôlée. Le nom envoyé par le navigateur ne détermine donc ni le répertoire de stockage ni le nom final sur disque, ce qui empêche les collisions et les tentatives de traversal telles que `../../secret.pdf`.

Avant stockage, `ArchiveForm` rejette les extensions hors allowlist, les fichiers vides et les fichiers qui dépassent `ARCHIVE_MAX_UPLOAD_SIZE`. Le type MIME déclaré est confronté aux formats attendus lorsqu’il est fourni, et une signature minimale est contrôlée pour PDF (`%PDF-`), PNG et JPEG. Le type MIME transmis par le client peut être falsifié ; l’extension, le MIME et les signatures réduisent le risque sans prouver qu’un fichier est inoffensif. Le MVP ne fournit ni antivirus, ni analyse anti-malware, ni inspection exhaustive des formats Office.

`file_size` est calculé depuis le fichier réellement reçu et `uploaded_by` reste imposé par le serveur. `checksum` demeure vide : aucun calcul SHA-256 n’est anticipé avant T-013. Le formulaire d’édition retire le champ de fichier, interdisant tout remplacement silencieux avant une politique de versioning validée.

Le document privé n’est jamais lié par `archive.file.url`. La route `/archives/<pk>/download/` est protégée par `StaffRequiredMixin`; une requête anonyme est redirigée vers la connexion et un compte authentifié non staff reçoit HTTP 403. La vue utilise `FileResponse` avec une pièce jointe, traite une archive sans fichier ou un fichier manquant par HTTP 404, et ne supprime pas la métadonnée dans ce dernier cas. La restriction staff reste une mesure temporaire deny-by-default qui sera remplacée par le RBAC métier au T-011.


## RBAC métier et confidentialité — T-011

La politique d’autorisation est centralisée dans `archives.permissions`. Elle distingue l’authentification, qui établit l’identité, de l’autorisation, qui détermine le périmètre d’archives et les actions permises. Aucun écran d’archives ne décide seul à partir de `is_staff` ni ne répète une condition `user.role` dans les vues. Les rôles métier valides et le superuser technique sont traités dans une seule source de vérité ; un rôle absent ou invalide conduit au deny-by-default.

La confidentialité est appliquée avant toute recherche et pagination par `visible_archives_for`. Un Consultant ne reçoit que les archives PUBLIC ; un Agent reçoit PUBLIC et INTERNAL ; un Administrateur métier et un superuser reçoivent tous les niveaux. Cette restriction au niveau QuerySet évite les fuites par liste, recherche exacte, compteur de résultats, pagination, filtres ou indicateurs du dashboard. Les référentiels proposés en recherche proviennent également du périmètre visible.

Une archive hors périmètre produit HTTP 404 dans le détail, l’édition ciblée et le téléchargement. Cette réponse ne confirme pas qu’un identifiant correspond à une archive confidentielle existante. Une action interdite sur une archive déjà visible, telle qu’un Consultant qui tente de modifier une archive PUBLIC, retourne HTTP 403. Le téléchargement réutilise le même QuerySet autorisé que le détail ; l’URL directe ne permet donc pas de contourner le RBAC.

Les formulaires reçoivent l’utilisateur de la requête. Ils limitent les choix de confidentialité visibles et valident de nouveau la valeur soumise : un Agent ne peut pas créer ou transformer une archive en CONFIDENTIAL via un POST falsifié. Masquer un bouton ou une option améliore l’interface, mais le contrôle serveur reste l’autorité de sécurité. La politique actuelle reste provisoire et n’introduit ni ACL par service, ni règle nominative, ni audit.


## Journal d’audit métier — T-012

Le journal `AuditLog` trace les opérations métier sensibles après leur réussite : connexion, déconnexion, création, modification, consultation et téléchargement d’archive. Il est distinct des logs de serveur, qui servent au diagnostic technique. Les listes et recherches d’archives ne sont pas journalisées afin d’éviter le bruit et de limiter la collecte.

Les entrées sont créées uniquement par `record_audit_event` ou par les signaux de connexion et déconnexion. Les utilisateurs métier ne disposent d’aucune vue de création, modification ou suppression du journal ; l’interface Django Admin désactive également ces opérations. Cette garantie est **append-only au niveau applicatif** : elle limite les modifications depuis l’application mais ne remplace ni un SIEM externe, ni un stockage immuable, ni un chaînage cryptographique de production.

Les détails JSON sont normalisés à `source` et `changed_fields`. Le service ne conserve ni mot de passe, hash de mot de passe, formulaire POST complet, cookie, session, en-tête Authorization, contenu de fichier ou chemin privé. La référence documentaire est suffisante pour relier l’événement à l’archive sans recopier de métadonnées confidentielles.

L’adresse IP provient de `REMOTE_ADDR` lorsqu’elle est présente et valide. `X-Forwarded-For` n’est pas interprété par le MVP, car aucun proxy de confiance n’est encore validé pour cette information. Une IP indisponible est stockée à `NULL`. Les événements d’archive ne sont créés qu’après les contrôles RBAC : une tentative 404 ou 403 n’est pas présentée comme une consultation ou un téléchargement réussi.

La page `/audit/` est exclusivement accessible à l’Administrateur métier et au superuser ; un Agent ou Consultant reçoit HTTP 403, et un anonyme est redirigé vers la connexion. Cette restriction est nécessaire car le journal peut référencer des archives CONFIDENTIAL, même si un Agent ne peut pas les consulter directement.


## Intégrité des fichiers SHA-256 — T-013

T-013 utilise SHA-256 comme empreinte déterministe de référence pour détecter une altération du contenu stocké. Le checksum est calculé sur le fichier réellement enregistré dans le stockage privé, par blocs de 64 KiB, puis conservé dans `Archive.checksum`. Le client ne peut pas proposer cette valeur par POST, query string ou en-tête.

Une vérification contrôlée compare l’empreinte recalculée à la référence et retourne un état explicite. `MISMATCH` signale que le contenu actuel ne produit plus la même empreinte ; il ne remplace jamais le checksum historique. Les cas sans fichier, sans empreinte, fichier absent et erreur de lecture sont distingués afin d’éviter un faux résultat `VALID` ou une erreur HTTP non maîtrisée.

La route de vérification utilise POST avec CSRF et le QuerySet RBAC déjà appliqué au détail : un utilisateur peut vérifier uniquement une archive qu’il peut consulter. Une archive hors périmètre répond 404. Toute vérification est auditée sous `ARCHIVE_INTEGRITY_CHECK` avec le seul résultat autorisé ; les deux hashes complets ne sont pas dupliqués dans l’audit.

> SHA-256 dans ce MVP n’est **ni un chiffrement, ni une signature électronique, ni un contrôle d’accès, ni un antivirus, ni une preuve absolue de non-répudiation**. Il permet de détecter une différence entre le fichier actuel et l’empreinte de référence conservée.

Un acteur ayant simultanément le contrôle complet du stockage et de la base pourrait modifier le fichier et son checksum. Une signature numérique, un stockage immuable ou une infrastructure de confiance séparée serait nécessaire pour une garantie plus forte. De même, une modification concurrente du fichier pendant sa lecture (TOCTOU) peut théoriquement influencer le résultat ; ce risque et la vérification automatique à chaque téléchargement restent hors périmètre MVP.


## Revue transverse et durcissement — T-014

La revue T-014 confirme la présence conjointe des contrôles suivants : authentification Django, refus des comptes inactifs, neutralisation des redirections `next` externes, cookies HTTPOnly/SameSite, CSRF sur les opérations mutables, RBAC côté serveur, 404 anti-inférence, échappement Django, ORM sans SQL brut applicatif, stockage privé et audit minimal append-only applicatif. La matrice `HARD-001` à `HARD-026` vérifie les accès directs par identifiant, le mass assignment, le XSS, les recherches injection-like, les traversals, le fichier absent, l’audit, le checksum et la configuration d’hôtes de production.

Hors DEBUG, `DJANGO_ALLOWED_HOSTS` doit contenir des noms d’hôtes explicitement prévus pour le déploiement. Une valeur vide comme le wildcard `*` provoque `ImproperlyConfigured` au chargement des paramètres. Cette règle n’affecte pas le développement local, qui conserve les hôtes `localhost` et `127.0.0.1`. Le test `HARD-026` emploie des sous-processus Python isolés et confirme que `c-tech.example` ainsi que `c-tech.example,www.c-tech.example` sont acceptés en production, tandis que `*` est refusé.

Le contrôle `python manage.py check --deploy` signale volontairement en développement les paramètres propres à HTTPS et `DEBUG`. Ces avertissements ne sont pas masqués. Dans un profil production simulé avec HTTPS, cookies secure, redirection SSL et HSTS activés, le contrôle est sans warning seulement lorsque le preload HSTS est explicitement activé. Le preload reste une décision d’infrastructure à valider une fois le domaine et ses sous-domaines entièrement HTTPS.

La sécurité de production requiert encore une configuration reverse proxy/web server : limites de taille et de durée de requête, HTTPS final, redirection, sauvegardes, monitoring et réponse à incident. Une protection contre le brute-force/credential stuffing, un antivirus, une gestion centralisée des vulnérabilités de dépendances, une signature numérique et une immutabilité externe des logs ne sont pas fournis par le MVP et ne doivent pas être présentés comme tels.
