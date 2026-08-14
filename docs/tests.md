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

## Couverture ajoutée par T-006

| Référence | Scénario | Résultat attendu |
|---|---|---|
| AUTH-001 | Accès anonyme à la page protégée | Redirection vers `/accounts/login/` avec destination locale |
| AUTH-002 | Connexion valide | Session créée et redirection vers la page protégée |
| AUTH-003 | Mot de passe erroné | Authentification refusée et message générique |
| AUTH-004 | Utilisateur inconnu | Authentification refusée avec le même message générique |
| AUTH-005 | Utilisateur inactif | Authentification refusée, sans session créée |
| AUTH-006 | Utilisateur connecté | Accès HTTP 200 à la page protégée |
| AUTH-007 | Déconnexion POST | Session invalidée puis nouvelle redirection vers login |
| AUTH-008 | CSRF | Soumission de connexion sans jeton CSRF refusée par HTTP 403 |
| AUTH-009 | `next` local | Destination locale demandée après connexion acceptée |
| AUTH-010 | `next` externe | Destination externe arbitraire neutralisée par Django |

## Scénario de démonstration pour la soutenance

1. Ouvrir `/` sans connexion et constater la redirection vers la connexion.
2. Saisir de mauvais identifiants et constater le refus générique.
3. Saisir un username et un mot de passe valides, puis accéder à la page protégée.
4. Envoyer le formulaire de déconnexion.
5. Revenir sur `/` et constater que la redirection vers la connexion est de nouveau appliquée.

Ce scénario ne démontre pas encore les droits métier sur les archives : il prouve seulement l’identité, la session, le contrôle de la vue protégée et la déconnexion sécurisée.

## Couverture ajoutée par T-007

| Référence | Scénario | Résultat attendu |
|---|---|---|
| DASH-001 | Accès anonyme | Redirection vers la connexion |
| DASH-002 | Accès authentifié | Réponse HTTP 200 et tableau de bord rendu |
| DASH-003 | Base vide | Zéro pour les métriques agrégées, sans liste détaillée |
| DASH-004 | Compteur total | Nombre d’archives conforme à PostgreSQL |
| DASH-005 | Compteurs de statut | Archives actives et archivées distinguées |
| DASH-006 | Référentiels actifs | Seuls les services, catégories et types actifs sont comptabilisés |
| DASH-007 | Métadonnée confidentielle | Référence et titre d’une archive confidentielle absents du HTML |
| DASH-008 | Agrégats avec plusieurs archives | Total et compteurs de statut restent exacts |
| DASH-009 | Données sensibles | Ni checksum, hash de mot de passe ni titre confidentiel dans le HTML |
| DASH-010 | Contexte de vue | Aucun `latest_archives` ni libellé de liste détaillée |

## Fiche pédagogique — Tableau de bord

Un **dashboard** est une vue synthétique qui présente les informations importantes du système. Les nombres affichés proviennent de requêtes ORM exécutées sur PostgreSQL ; ils ne sont donc jamais inscrits en dur dans le HTML. Un **QuerySet** représente une requête Django vers la base de données. Dans le périmètre corrigé de T-007, la vue ne retourne que des agrégats : elle n’a donc pas besoin de `select_related` ni de relations documentaires individuelles.

Il n’existe pas encore de section « activité récente » car `AuditLog` n’est pas implémenté. La liste des dernières archives est elle aussi volontairement absente : l’authentification existe, mais la politique RBAC et de confidentialité documentaire n’est pas encore définie au ticket T-011.

### Scénario de démonstration

Après connexion, ouvrir le dashboard et montrer les compteurs d’archives, de services et de catégories. Expliquer que les valeurs proviennent directement de PostgreSQL et qu’aucune archive individuelle n’est affichée avant T-011. Cette démonstration doit durer entre 30 et 45 secondes et ne doit pas être confondue avec les futurs CRUD, recherche, audit ou RBAC.

### Question jury — Pourquoi les derniers documents ne sont-ils pas affichés ?

> Parce que l’authentification existe déjà, mais la politique d’autorisation détaillée des archives n’est pas encore implémentée. Afficher les dernières archives à tous les utilisateurs authentifiés pourrait révéler des métadonnées confidentielles. Nous avons donc préféré attendre le contrôle d’accès du ticket RBAC plutôt que d’implémenter une règle de sécurité partielle.

## Couverture ajoutée par T-008

| Références | Contrôle vérifié |
|---|---|
| CRUD-001 à CRUD-003 | Redirection de l’anonyme, refus HTTP 403 du non-staff et accès du staff |
| CRUD-004 à CRUD-006 | Liste autorisée, création valide et attribution serveur de `uploaded_by` |
| CRUD-007 à CRUD-008 | Ignorance des tentatives de manipulation de `uploaded_by` et `checksum` |
| CRUD-009 | Référence unique validée côté serveur |
| CRUD-010 à CRUD-012 | Détail, modification et invariance des champs protégés |
| CRUD-013 | Absence de route de suppression physique |
| CRUD-014 à CRUD-015 | Refus CSRF de création et de modification sans jeton |
| CRUD-016 à CRUD-017 | Référentiels actifs à la création et conservation d’un référentiel historique inactif à l’édition |
| CRUD-018 | Persistance de `CONFIDENTIAL` sans règle d’autorisation prématurée |
| CRUD-019 | Échappement XSS du titre dans le détail |
| CRUD-020 | Réponse HTTP 404 pour une archive absente |

## Fiche pédagogique — CRUD de métadonnées

**CRUD** signifie *Create, Read, Update, Delete*. Dans cette version, la création, la consultation et la modification sont fournies, mais la suppression physique est volontairement reportée : une archive possède une valeur historique et C-Tech doit d’abord valider une politique de conservation. Un **ModelForm** est un formulaire Django lié à un modèle. Il n’utilise pas `fields="__all__"` ici afin que l’utilisateur ne puisse pas contrôler des champs techniques.

`uploaded_by` est attribué côté serveur à l’utilisateur connecté. La validation HTML améliore l’expérience, mais la validation Django et les contraintes PostgreSQL restent l’autorité finale. Les écrans sont temporairement limités à `is_staff` car le RBAC métier complet n’est pas encore défini ; cette stratégie restrictive évite d’exposer les archives avant T-011.

### Question jury — Pourquoi appeler T-008 CRUD sans DELETE ?

> Le parcours CRUD est construit autour de la création, de la consultation et de la modification, mais la suppression physique a volontairement été exclue tant que la politique de conservation de C-Tech n’est pas connue. Pour un système d’archives, supprimer un enregistrement sans règle de conservation validée serait plus dangereux que de reporter cette fonctionnalité.


## Couverture ajoutée par T-009

| Référence | Scénario | Résultat attendu |
|---|---|---|
| SEARCH-001 | Requête anonyme sur la liste | Redirection vers la connexion avec la destination demandée |
| SEARCH-002 | Compte authentifié non staff | Réponse HTTP 403, même sans exception côté interface |
| SEARCH-003 | Compte staff | Réponse HTTP 200 et formulaire de recherche disponible |
| SEARCH-004 | Recherche partielle par référence | L’archive dont la référence contient le terme est retournée |
| SEARCH-005 | Recherche de titre sans casse | Une casse différente du terme retourne l’archive concernée |
| SEARCH-006 | Recherche dans la description | Le terme présent dans `description` retourne l’archive concernée |
| SEARCH-007 | Recherche sans résultat | Compteur à zéro et état vide spécifique aux critères affiché |
| SEARCH-008 | Filtre `category` | Seules les archives de la catégorie choisie sont listées |
| SEARCH-009 | Filtre `document_type` | Seules les archives du type choisi sont listées |
| SEARCH-010 | Filtre `service` | Seules les archives du service choisi sont listées |
| SEARCH-011 | Filtre `status` | Les valeurs `ACTIVE` et `ARCHIVED` sont distinguées |
| SEARCH-012 | Filtre `confidentiality_level` | Le filtre métadonnée fonctionne sans prétendre valider une autorisation |
| SEARCH-013 | Borne inférieure de date | La date `document_date_from` est inclusive (`>=`) |
| SEARCH-014 | Borne supérieure de date | La date `document_date_to` est inclusive (`<=`) |
| SEARCH-015 | Intervalle de dates | Les deux bornes sont appliquées conjointement |
| SEARCH-016 | Intervalle invalide | Erreur de formulaire affichée et aucun résultat retourné |
| SEARCH-017 | Critères combinés | `q`, `service` et `status` réduisent conjointement le jeu de résultats |
| SEARCH-018 | Pagination de plus de 20 résultats | La page 1 contient 20 éléments, la page 2 contient le reliquat |
| SEARCH-019 | Conservation des filtres | Le lien de page suivante conserve la query string hors `page` |
| SEARCH-020 | Entrée de type injection SQL | Le texte est recherché littéralement et ne contourne aucun filtre |
| SEARCH-021 | Entrée XSS | Le terme est échappé dans le HTML et aucune balise script n’est rendue |
| SEARCH-022 | Données sensibles | Ni checksum ni hash de mot de passe n’apparaissent dans les résultats |
| SEARCH-023 | Recherche `q` vide | La liste normale est retournée sans erreur |
| SEARCH-024 | Archive sans date documentaire | Le filtre de date ne produit pas d’erreur et écarte naturellement la valeur `NULL` |

Les scénarios SEARCH-001 à SEARCH-024 sont regroupés dans `ArchiveSearchTests`. Ils complètent les soixante-dix scénarios précédemment intégrés et portent la cible du ticket à au moins quatre-vingt-quatorze tests réussis, sans migration supplémentaire.

## Fiche pédagogique — recherche GET, objets `Q` et ORM

Une recherche est une **lecture** : elle ne crée, ne modifie ni ne supprime une archive. Elle emploie donc GET, ce qui place les critères dans l’URL. Cette forme permet de rafraîchir, mettre en favori, partager un lien et passer à une autre page tout en conservant exactement les filtres utilisés. À l’inverse, POST est réservé aux opérations mutables, comme la création ou la modification d’une archive, car il porte une intention de changement et nécessite un jeton CSRF.

Un **QuerySet** est la représentation Django d’une requête vers la base de données. La vue démarre avec l’ensemble des archives puis ajoute les restrictions seulement lorsqu’un critère valide est fourni. Un objet `Q` permet d’exprimer une condition composée ; ici, une même recherche textuelle correspond à la référence **ou** au titre **ou** à la description. Les filtres structurés sont ensuite appliqués avec des `AND`, ce qui rend les critères combinables et lisibles.

L’ORM transforme ces expressions Python en requêtes paramétrées pour PostgreSQL. Le code ne compose pas de SQL depuis une saisie utilisateur. La recherche simple de T-009 suffit pour le volume et les besoins actuels : aucune technologie de plein texte ou de recherche sémantique n’est introduite avant qu’un besoin mesuré ne le justifie.

### Question jury — Pourquoi utiliser GET pour la recherche ?

> Parce qu’une recherche ne change pas l’état du système. GET rend les critères visibles et réutilisables dans l’URL, facilite la pagination et évite de traiter une simple consultation comme une opération métier mutable. Les formulaires qui écrivent des données restent, eux, en POST avec CSRF.


## Couverture ajoutée par T-010

| Référence | Scénario | Résultat attendu |
|---|---|---|
| FILE-001 | Upload PDF synthétique valide | Archive créée, fichier enregistré sous stockage privé et `file_size` réel persistant |
| FILE-002 | Manipulation de `uploaded_by` | Le serveur conserve l’utilisateur de la requête |
| FILE-003 | Manipulation de `file_size` | La valeur POST est ignorée au profit de la taille réelle du fichier |
| FILE-004 | Extension interdite | Formulaire invalide et aucun fichier persistant |
| FILE-005 | Fichier au-delà de la limite | Formulaire invalide et aucun fichier persistant |
| FILE-006 | Fichier vide | Formulaire invalide |
| FILE-007 | Faux PDF | Signature PDF absente, fichier refusé |
| FILE-008 | Nom avec traversal | Le chemin final reste sous le répertoire privé configuré |
| FILE-009 | Deux noms clients identiques | Deux noms physiques UUID distincts sont créés |
| FILE-010 | Écran de détail | Lien vers la route contrôlée, sans URL ou chemin direct de stockage |
| FILE-011 | Téléchargement anonyme | Redirection vers la connexion |
| FILE-012 | Téléchargement non staff | Réponse HTTP 403 |
| FILE-013 | Téléchargement staff | HTTP 200, pièce jointe et contenu synthétique attendu |
| FILE-014 | Archive inconnue | Réponse HTTP 404 |
| FILE-015 | Archive sans fichier | Réponse HTTP 404 sans erreur serveur |
| FILE-016 | Fichier absent sur disque | Réponse HTTP 404 et métadonnée conservée |
| FILE-017 | Upload sans CSRF | Réponse HTTP 403 et aucun fichier persistant |
| FILE-018 | Modification de métadonnées avec fichier joint | Le fichier original ne change pas |
| FILE-019 | Nom d’origine avec HTML | Aucune balise active ni chemin privé rendu dans le détail |
| FILE-020 | Jeux de tests | Utilisation exclusive de `SimpleUploadedFile` synthétique |

Les scénarios de fichiers utilisent `TemporaryDirectory` et `override_settings(PRIVATE_MEDIA_ROOT=...)`. Ils ne laissent donc aucun fichier dans le répertoire privé réel du projet. Ces vingt tests s’ajoutent aux quatre-vingt-quatorze tests précédents et portent la suite à cent quatorze scénarios automatisés.

## Fiche pédagogique — fichier privé et validation de téléversement

Un `FileField` ne place pas le contenu du document dans PostgreSQL : la base conserve les métadonnées et le chemin relatif, tandis que Django Storage écrit le contenu dans le répertoire configuré. Le nom physique est généré par le serveur avec un UUID. Ce choix évite qu’un nom client tel que `rapport.pdf` ou `../../secret.pdf` détermine le chemin réel ou écrase un document existant.

Un type MIME est une indication sur le format d’un fichier. Le navigateur peut le déclarer, mais cette valeur n’est pas une preuve et peut être falsifiée. Le MVP combine donc l’extension, le MIME déclaré lorsqu’il est disponible et quelques signatures simples, par exemple `%PDF-` pour un PDF. Ces contrôles sont utiles mais ne remplacent pas un antivirus ou une analyse de contenu spécialisée.

Le répertoire privé n’est jamais rendu public par une URL. `FileResponse` permet à Django de lire le fichier seulement après les contrôles d’accès de la vue, puis de proposer le document en pièce jointe. Le remplacement libre d’un fichier est volontairement absent : une archive documentaire requiert une future politique de versioning, de conservation et d’audit avant qu’un nouveau contenu puisse remplacer l’ancien.

### Questions jury — réponses attendues

> **« Un exécutable renommé en PDF est-il sûr ? »** Non. L’extension seule ne suffit pas. Le MVP croise plusieurs signaux de format, mais ne prétend pas remplacer une solution antivirus/anti-malware de production.

> **« Pourquoi ne pas publier les fichiers dans `/media/` ? »** Une URL publique pourrait contourner les autorisations. Le document reste dans un stockage privé et la vue Django contrôle l’utilisateur avant de renvoyer une pièce jointe.


## Couverture ajoutée par T-011

| Références | Contrôle vérifié |
|---|---|
| RBAC-001 à RBAC-004 | Redirection anonyme puis accès HTTP 200 à la liste pour Administrateur, Agent et Consultant |
| RBAC-005 à RBAC-010 | Visibilité de liste conforme à PUBLIC, INTERNAL et CONFIDENTIAL selon le rôle |
| RBAC-011 à RBAC-014 | Recherche exacte d’archives invisibles sans résultat ; recherche Administrateur autorisée |
| RBAC-015 à RBAC-018 | Détail direct d’une archive hors périmètre en HTTP 404 ; Administrateur autorisé |
| RBAC-019 à RBAC-023 | Création refusée au Consultant, autorisée à l’Agent pour PUBLIC/INTERNAL et à l’Administrateur pour CONFIDENTIAL |
| RBAC-024 à RBAC-028 | Modification refusée au Consultant, autorisée à l’Agent sur le périmètre visible et protection contre l’escalade vers CONFIDENTIAL |
| RBAC-029 à RBAC-034 | Téléchargement selon la même règle de visibilité que le détail |
| RBAC-035 | Non-inférence : liste, pagination, recherche exacte et dashboard d’un Consultant n’exposent pas les archives CONFIDENTIAL |
| RBAC-036 à RBAC-037 | Compteurs de dashboard limités au périmètre Agent ou Administrateur |
| RBAC-038 | Superuser technique avec accès complet documenté |
| RBAC-039 à RBAC-040 | Navigation Consultant sans actions mutables ; Agent avec les actions autorisées |

Les quarante scénarios `ArchiveRbacTests` s’ajoutent aux cent quatorze scénarios précédents et portent la suite à cent cinquante-quatre tests. Ils utilisent uniquement des archives et fichiers PDF synthétiques stockés dans des répertoires temporaires.

## Fiche pédagogique — RBAC, QuerySet et non-inférence

**RBAC** signifie *Role-Based Access Control*. L’authentification répond à la question « qui est connecté ? » ; l’autorisation répond à « quelles archives et quelles actions cette personne peut-elle consulter ou effectuer ? ». Dans le MVP, le rôle métier donne un périmètre de confidentialité provisoire : tous les niveaux pour un Administrateur, PUBLIC et INTERNAL pour un Agent, PUBLIC seulement pour un Consultant.

Un **QuerySet** filtré est une protection essentielle : l’application part des seules archives visibles avant de chercher, filtrer, paginer ou compter. Contrôler uniquement la page détail serait insuffisant, car un titre exact, un compteur ou une page supplémentaire pourrait alors révéler qu’une archive confidentielle existe. Une archive invisibile retourne HTTP 404, afin de ne pas distinguer un identifiant inexistant d’un document auquel le rôle n’a pas accès.

Le détail et le téléchargement appliquent la même politique que la liste. L’interface masque aussi les actions interdites, mais cette mesure n’est pas une sécurité : un navigateur peut envoyer un POST manuel ou saisir une URL. Les vues et formulaires vérifient donc toujours l’autorisation côté serveur.

### Question jury — Comment un Consultant ne peut-il pas deviner une archive confidentielle ?

> Le QuerySet est filtré selon le rôle avant toute liste, recherche, pagination ou agrégation. Les vues objet réutilisent cette règle et retournent 404 pour une archive hors périmètre. Même avec l’identifiant ou le titre, l’utilisateur ne reçoit ni objet, ni compteur, ni confirmation de son existence.


## Couverture ajoutée par T-012

| Références | Contrôle vérifié |
|---|---|
| AUDIT-001 à AUDIT-003 | Connexion et déconnexion réelles journalisées ; aucun mot de passe dans un LOGIN |
| AUDIT-004 à AUDIT-008 | Création et modification réussies journalisées ; invalidité, refus RBAC et escalade exclus ; `changed_fields` minimal |
| AUDIT-009 à AUDIT-013 | Consultation et téléchargement autorisés journalisés ; 404, refus et fichier absent exclus |
| AUDIT-014 à AUDIT-016 | `REMOTE_ADDR`, IP absente et horodatage déterminé côté serveur |
| AUDIT-017 à AUDIT-019 | Acteur et archive corrects ; détails sans mot de passe, hash ni session |
| AUDIT-020 à AUDIT-024 | Route `/audit/` refusée à l’Agent et au Consultant, ouverte à l’Administrateur/superuser, redirection anonyme |
| AUDIT-025 à AUDIT-026 | Pagination à 25 événements et ordre décroissant stable |
| AUDIT-027 à AUDIT-029 | Administration Django en lecture seule, sans ajout ni suppression |
| AUDIT-030 | Liste et recherche d’archives sans bruit de logs de consultation |

Les trente scénarios `AuditLogTests` s’ajoutent aux cent cinquante-quatre tests précédents et portent la suite à cent quatre-vingt-quatre tests. Ils emploient seulement des utilisateurs et fichiers synthétiques ; les répertoires privés sont isolés dans des `TemporaryDirectory`.

## Fiche pédagogique — audit métier et append-only

Un **journal d’audit** est un historique structuré d’opérations métier importantes : qui a fait quoi, sur quelle archive, quand et depuis quelle adresse IP si elle est disponible. Il ne remplace pas les logs techniques d’un serveur web, qui servent principalement au fonctionnement et au diagnostic.

Le terme **append-only** signifie qu’à l’échelle applicative les événements sont ajoutés par le système, sans écran métier de modification ni suppression. Cette mesure rend plus difficile l’effacement d’une trace dans l’application, mais elle ne constitue pas une immutabilité cryptographique. Une architecture de production à exigences élevées pourrait compléter ce choix par un SIEM, un stockage externe ou un mécanisme d’intégrité des journaux.

Les détails d’audit doivent être **minimaux**. Enregistrer `changed_fields=["title", "status"]` suffit à expliquer une modification sans recopier les valeurs avant/après, le fichier, les secrets ou les données personnelles inutiles. L’adresse IP apporte un contexte d’origine, mais ne prouve pas à elle seule l’identité ; le MVP ne fait confiance qu’à `REMOTE_ADDR` et ignore `X-Forwarded-For` tant qu’un proxy de confiance n’est pas défini.

### Question jury — Un administrateur peut-il modifier les logs pour cacher son activité ?

> Dans l’application, le journal est append-only : aucune fonction métier ne permet de modifier ou supprimer une entrée, et l’administration Django est configurée en lecture seule. Cette protection reste applicative ; un stockage externe ou immuable serait requis pour une garantie de production plus forte.


## Couverture ajoutée par T-013

| Références | Contrôle vérifié |
|---|---|
| HASH-001 à HASH-002 | Empreinte connue, lecture par blocs et mémoire bornée par chunk |
| HASH-003 à HASH-005 | Calcul automatique après upload, checksum client ignoré et format hexadécimal de 64 caractères |
| HASH-006 à HASH-011 | États `NO_FILE`, `MISSING_CHECKSUM`, `VALID`, `MISMATCH`, conservation de la référence et `FILE_MISSING` |
| HASH-012 | Restauration de la position initiale d’un flux repositionnable |
| HASH-013 à HASH-018 | Redirection anonyme et visibilité RBAC identique au détail pour Consultant, Agent et Administrateur |
| HASH-019 | Vérification POST soumise à CSRF |
| HASH-020 à HASH-022 | Événement `ARCHIVE_INTEGRITY_CHECK` pour VALID/MISMATCH et détail limité au résultat autorisé |
| HASH-023 à HASH-024 | Absence de recalcul sur liste, recherche et téléchargement |

Les vingt-quatre scénarios d’intégrité s’ajoutent aux cent quatre-vingt-quatre tests précédents et portent la suite à deux cent huit tests. Les fichiers et altérations de démonstration sont exclusivement synthétiques et isolés dans des stockages temporaires.

## Fiche pédagogique — empreinte SHA-256

Un **hash** est une fonction qui transforme un contenu en empreinte de taille fixe. Dans le cas de SHA-256, l’empreinte est représentée par soixante-quatre caractères hexadécimaux. Le même contenu produit toujours la même empreinte ; un contenu modifié produit en pratique une empreinte différente. Le calcul est réalisé par blocs de 64 KiB afin d’éviter de charger le fichier entier en mémoire.

Le checksum enregistré lors du dépôt est la **référence historique**. Lors d’une vérification, l’application recalcule l’empreinte du fichier actuellement stocké et compare les deux valeurs. `VALID` signifie qu’elles correspondent ; `MISMATCH` signifie que le contenu actuel n’est plus identique à la référence. La référence n’est pas remplacée lors d’un mismatch, car elle est précisément nécessaire pour détecter l’altération.

SHA-256 n’est pas du chiffrement réversible : on ne peut pas retrouver pratiquement le fichier depuis son empreinte. Il ne protège pas non plus contre un acteur qui modifierait simultanément le fichier et la valeur en base. Une signature numérique, une infrastructure séparée ou un stockage immuable serait nécessaire pour répondre à ce niveau de menace.

### Question jury — Si quelqu’un modifie le fichier et le checksum dans la base en même temps ?

> Le mécanisme actuel détecte une différence entre le fichier et l’empreinte de référence conservée. Un acteur ayant un contrôle complet simultané du stockage et de la base pourrait modifier les deux. Une protection plus forte demanderait une signature numérique, un stockage immuable ou une infrastructure de confiance séparée, ce qui dépasse le périmètre du MVP.


## Couverture ajoutée par T-014

| Références | Contrôle transverse |
|---|---|
| HARD-001 à HARD-004 | IDOR sur détail, édition, téléchargement et vérification d’intégrité |
| HARD-005 | Mass assignment des champs serveur et indicateurs de privilège |
| HARD-006 à HARD-008 | Échappement XSS et traitement ORM des recherches injection-like |
| HARD-009 à HARD-011 | Path traversal Unix/Windows et absence d’exposition publique du stockage privé |
| HARD-012 à HARD-014 | Absence de données sensibles dans l’audit et administration AuditLog read-only |
| HARD-015 à HARD-018 | ID malformé, fichier manquant, mismatch conservant la référence et deny-by-default |
| HARD-019 à HARD-020 | Refus d’un compte inactif et neutralisation de `next` externe |
| HARD-021 à HARD-024 | CSRF create/update/intégrité et logout uniquement par POST CSRF |
| HARD-025 | Secret d’environnement requis et absence de fixture secrète ou `ALLOWED_HOSTS=*` dans le modèle d’environnement |

T-014 complète les tests existants au lieu de les dupliquer. Les scénarios d’authentification détaillés restent dans `accounts.tests`, les matrices RBAC dans `archives.tests`, les contrôles fichiers dans `ArchiveFileHandlingTests`, l’audit dans `audit.tests` et l’intégrité dans `ArchiveIntegrityTests`. La nouvelle suite concentre les croisements entre ces mécanismes, avec des données et fichiers strictement synthétiques.

Le contrôle `check --deploy` est exécuté en développement et dans un profil production simulé. Ses avertissements de développement sont conservés et classifiés dans [`security-review.md`](security-review.md) ; aucun warning n’est masqué.
