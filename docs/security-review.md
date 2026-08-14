# Revue de sécurité du MVP — T-014

## Périmètre de la revue

Cette revue couvre le MVP C-Tech Archives après intégration de T-013. Elle examine les routes exposées, l’authentification par session, le RBAC métier, le stockage privé, les formulaires, l’audit append-only applicatif, l’intégrité SHA-256 et la configuration Django. Elle ne constitue ni une certification OWASP, ni un test d’intrusion externe, ni une garantie de sécurité totale.

La baseline de départ est le commit de fusion T-013 `9b05c31c5437e443bfa3e50a1fd077c44c439f23`, avec 208 tests. T-014 ajoute la matrice `HARD-001` à `HARD-026`, exécutée contre une base de tests PostgreSQL et des fichiers synthétiques isolés. Le scénario `HARD-026` charge les paramètres dans des sous-processus Python isolés afin de vérifier la configuration réellement appliquée en production.

## Modèle de menace simplifié

| Élément | Menace principale | Contrôle vérifié | Limite explicitement conservée |
|---|---|---|---|
| Identifiants et session | Connexion illégitime, fixation ou détournement de session | Auth Django, mots de passe hachés, session HTTPOnly/SameSite, CSRF | Pas de MFA ni de limitation de tentatives native |
| Métadonnées d’archives | Accès inter-rôle ou IDOR | RBAC centralisé, QuerySet visible, 404 anti-inférence | Pas d’ACL par service ou par individu |
| Fichiers privés | Publication accidentelle, traversal, upload malveillant | Stockage hors `MEDIA_URL`, UUID côté serveur, allowlist, signatures simples, vue contrôlée | Pas d’antivirus ni de scan profond de formats Office |
| Journal d’audit | Consultation, modification ou suppression non autorisée | Vue Administrateur, Admin Django read-only, API d’écriture centralisée | Pas d’immutabilité externe/WORM |
| Checksum de référence | Altération non détectée du fichier | SHA-256 post-stockage, vérification explicite, audit minimal | Pas de signature numérique ni de stockage immuable |

Les acteurs considérés sont un attaquant anonyme, un Consultant authentifié, un Agent d’archives authentifié, un Administrateur, un compte compromis et un superuser technique. Les menaces examinées sont l’accès non autorisé, l’IDOR, la fuite de métadonnées, l’upload malveillant, l’altération de fichier, la manipulation d’audit, le XSS, l’injection, le path traversal et les attaques par identifiants.

## Matrice des surfaces applicatives

| Route | Méthode | Authentification | Autorisation | CSRF | Données sensibles | Audit | Statut attendu |
|---|---|---|---|---|---|---|---|
| `/` | GET | Oui | Rôle archive reconnu | N/A | Agrégats du périmètre visible | Non | 302 anonyme, 200 autorisé |
| `/accounts/login/` | GET, POST | Non | Public | POST | Identifiants | LOGIN réussi seulement | 200/302, `next` externe neutralisé |
| `/accounts/logout/` | POST | Oui | Session courante | Oui | Session | LOGOUT réussi | 302 ; GET 405 ; POST sans CSRF 403 |
| `/archives/` | GET | Oui | QuerySet RBAC | N/A | Métadonnées visibles | Non | 302 anonyme, 200 rôle connu, 403 rôle invalide |
| `/archives/new/` | GET, POST | Oui | Administrateur/Agent | POST | Métadonnées et fichier | ARCHIVE_CREATE réussi | 403 Consultant, 302 succès |
| `/archives/<pk>/` | GET | Oui | Archive visible | N/A | Métadonnées visibles | ARCHIVE_VIEW réussi | 404 hors périmètre ou ID invalide |
| `/archives/<pk>/edit/` | GET, POST | Oui | Archive visible + rôle créateur | POST | Métadonnées | ARCHIVE_UPDATE si changement | 404 hors périmètre ; 403 action interdite |
| `/archives/<pk>/download/` | GET | Oui | Archive visible | N/A | Fichier privé | ARCHIVE_DOWNLOAD réussi | 404 hors périmètre ou fichier absent |
| `/archives/<pk>/verify-integrity/` | POST | Oui | Archive visible | Oui | Résultat d’intégrité seulement | ARCHIVE_INTEGRITY_CHECK | 404 hors périmètre ; 403 CSRF |
| `/audit/` | GET | Oui | Administrateur/superuser | N/A | Journal minimal | Non | 403 Agent/Consultant |
| `/admin/` | GET, POST | Oui | `is_staff` Django | POST | Administration technique | Admin Django | Auth Django ; AuditLog sans add/change/delete |

Aucune route métier `/audit/new/`, `/audit/<pk>/edit/` ou `/audit/<pk>/delete/` n’est déclarée. Aucun chemin vers `PRIVATE_MEDIA_ROOT` n’est inclus dans les URL Django.

## Contrôles vérifiés

La revue transversale confirme que le RBAC est appliqué avant le détail, l’édition, le téléchargement et la vérification SHA-256. Le Consultant ne voit que `PUBLIC`, l’Agent `PUBLIC` et `INTERNAL`, et l’Administrateur ainsi que le superuser technique voient tous les niveaux. Un objet hors périmètre répond 404, ce qui évite de confirmer son existence. Une action interdite sur un objet visible répond 403.

Les formulaires `ArchiveForm` utilisent une liste blanche de champs. Les champs `uploaded_by`, `file_size`, `checksum`, horodatages et indicateurs de privilège ne sont pas modifiables par POST. Le checksum est recalculé côté serveur après stockage du fichier. Les tests de mass assignment falsifient ces valeurs et confirment qu’elles ne modifient ni l’archive, ni le compte connecteur.

Les tests confirment l’échappement automatique des métadonnées et des requêtes de recherche contenant du HTML. Le balayage statique limité au code du projet n’a trouvé ni `mark_safe`, ni filtre `safe`, ni `format_html` applicatif. Il n’a trouvé ni `raw()`, ni `cursor.execute`, ni `extra()`, ni `RawSQL` dans le domaine ; les recherches utilisent l’ORM Django et les chaînes d’injection sont traitées comme des données.

Le stockage de fichiers est privé : le nom physique est généré côté serveur, les tentatives de traversal Unix et Windows restent sous `PRIVATE_MEDIA_ROOT`, et aucune route `/media/` ne sert un document d’archive. Les tests couvrent également l’absence de fichier, les extensions interdites, les signatures incohérentes, les fichiers vides et les collisions de nom déjà traitées par les tickets précédents.

Le journal `AuditLog` ne contient que des détails minimaux autorisés. Les parcours négatifs — 404 RBAC, 403 CSRF, formulaire invalide et fichier manquant — ne produisent pas de faux événement de succès. Django Admin refuse toute création, modification et suppression de log par ses méthodes de permission.

La vérification SHA-256 distingue `VALID`, `MISMATCH`, `NO_FILE`, `MISSING_CHECKSUM`, `FILE_MISSING` et `ERROR`. Un mismatch conserve le checksum de référence historique. Les listes, recherches, tableau de bord et téléchargements ne recalculent pas automatiquement l’empreinte afin d’éviter un coût I/O implicite.

## Mapping léger OWASP

| Catégorie de revue | Couverture MVP vérifiée | Limite |
|---|---|---|
| Broken Access Control | RBAC centralisé, QuerySet filtré, 404 anti-IDOR, tests detail/edit/download/verify | Pas d’ACL métier fine |
| Authentication Failures | Sessions Django, comptes inactifs refusés, `next` externe neutralisé, CSRF | Pas de MFA ni rate limiting |
| Injection | ORM, tests de paramètres SQL-like, absence de SQL brut dans le domaine | Aucun pentest SQL externe |
| Security Misconfiguration | Secrets environnement, hôtes explicites sans wildcard hors DEBUG, cookies/HTTPS pilotés par environnement, `check --deploy` | Déploiement reverse proxy non encore réalisé |
| Software and Data Integrity | Upload allowlist, stockage privé, checksum SHA-256, audit de vérification | Pas de signature numérique ou WORM |
| Logging and Monitoring | Audit métier minimal, consultation administrateur, Admin read-only | Pas d’alerting ni centralisation SIEM |

> Ce tableau est un **mapping de revue** : il ne constitue pas une certification OWASP ni une preuve d’absence de vulnérabilité.

## Résultats de configuration et déploiement

La commande `python manage.py check --deploy` exécutée dans le profil de développement a produit les warnings `security.W004`, `security.W008`, `security.W012`, `security.W016` et `security.W018`. Ils correspondent respectivement à HSTS, redirection HTTPS, cookies secure et DEBUG actifs en développement. Ils ne sont pas masqués, car le MVP garde volontairement le développement local en HTTP.

Dans un profil de production simulé avec `DJANGO_ENV=production`, `DJANGO_DEBUG=false`, cookies secure, redirection HTTPS et HSTS activés, le seul avertissement restant est `security.W021` tant que `DJANGO_SECURE_HSTS_PRELOAD=false`. Avec `DJANGO_SECURE_HSTS_PRELOAD=true`, `check --deploy` ne produit aucun warning. Le preload reste une décision de production à confirmer seulement une fois le domaine final entièrement HTTPS, y compris les sous-domaines, car cette option ne doit pas être activée aveuglément.

| Élément | État développement | Exigence production |
|---|---|---|
| `DEBUG` | Vrai par défaut local | `DJANGO_DEBUG=false` obligatoire |
| Cookies de session/CSRF | Secure désactivé localement | `DJANGO_SESSION_COOKIE_SECURE=true`, `DJANGO_CSRF_COOKIE_SECURE=true` |
| HTTPS | Redirection désactivée localement | `DJANGO_SECURE_SSL_REDIRECT=true` ou reverse proxy équivalent documenté |
| HSTS | 0 localement | `DJANGO_SECURE_HSTS_SECONDS=31536000` après HTTPS complet |
| HSTS preload | Désactivé par défaut | Décision explicite après validation domaine/sous-domaines |
| Hôtes | `localhost,127.0.0.1` en DEBUG | `DJANGO_ALLOWED_HOSTS` explicite, jamais `*` |
| Secret | Variable obligatoire | Secret unique fourni hors Git et renouvelable |

`pip-audit` n’était pas disponible localement, donc aucun résultat d’analyse de vulnérabilités de dépendances n’est revendiqué. La commande recommandée pour CI ou production est `python -m pip install pip-audit && pip-audit -r requirements.txt`, exécutée dans un environnement contrôlé.

## Findings et corrections

| ID | Gravité | Constat | Correction ou statut | Test de non-régression |
|---|---|---|---|---|
| F-014-001 | Informationnel | Les contrôles de sécurité sont déjà présents mais épars dans les tests de tickets antérieurs | Matrice transversale `HARD-001` à `HARD-026` ajoutée ; aucune faille significative reproduite | Suite T-014 |
| F-014-002 | Informationnel | `check --deploy` avertit correctement en profil local HTTP/DEBUG | Aucune suppression de warning ; profil production simulé documenté et validé | `check --deploy` développement et production |
| F-014-003 | Faible | Aucun scanner de dépendances n’est configuré dans le dépôt | Risque documenté ; commande CI/production recommandée, sans installation arbitraire de dépendance | Revue manuelle requirements |
| F-014-004 | Faible | Le wildcard `DJANGO_ALLOWED_HOSTS=*` était accepté en production, contrairement à la règle documentée d’hôtes explicites | Validation de configuration ajoutée dans `settings.py` : le wildcard provoque `ImproperlyConfigured` hors DEBUG | `HARD-026` (sous-processus isolé) |

## Risques résiduels et prérequis de production

Les risques résiduels assumés sont le brute-force et credential stuffing sans rate limiting intégré, l’absence de MFA, l’absence d’antivirus, l’absence de chiffrement de stockage géré par l’application, l’absence de signature numérique, l’absence d’immutabilité externe des logs et checksums, le risque TOCTOU sur une modification concurrente d’un fichier, ainsi que les limites d’upload du reverse proxy/web server à définir en production. `ARCHIVE_MAX_UPLOAD_SIZE` limite l’application ; les seuils et timeouts Nginx/équivalent doivent compléter cette défense contre les gros corps de requête et le DoS.

Sont hors périmètre : OAuth, JWT, API REST, MFA, S3, moteur antivirus maison, blockchain, signature électronique, chiffrement custom, microservices et workflow documentaire supplémentaire.

## Conclusion

Aucune vulnérabilité critique ou importante n’a été reproduite. Une faiblesse de configuration de faible gravité concernant `ALLOWED_HOSTS=*` a été identifiée et corrigée. Le MVP ne doit toutefois pas être présenté comme totalement sécurisé : il applique des contrôles mesurables et testés, avec des limites de production clairement documentées.
