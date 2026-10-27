# Déploiement sur Render — C-Tech Archives

Ce document décrit le déploiement de C-Tech Archives sur Render à partir du blueprint [`render.yaml`](../render.yaml), puis le diagnostic en cas de panne.

## 1. Ce que fait le blueprint

| Élément | Valeur |
|---|---|
| Service | Web Service Python, offre gratuite |
| Runtime | Python 3.13 (`PYTHON_VERSION`) |
| Framework | Django 5.2 LTS, servi par gunicorn (`WEB_CONCURRENCY`, 2 workers par défaut) |
| Statiques | WhiteNoise, `CompressedManifestStaticFilesStorage` (noms hachés, gzip, cache d’un an) |
| Base | PostgreSQL géré `ctech-postgres-db` |
| Santé | `healthCheckPath: /healthz/` : interroge la base et renvoie 200 ou 503 |

**Build** (`./build.sh`) : installation des versions figées (`pip install -r requirements.txt -c constraints.txt`) puis `collectstatic`.

**Démarrage** (`startCommand`), dans cet ordre :

1. `migrate --noinput` ;
2. `createcachetable` : table `ctech_cache` partagée par les workers pour la limitation des tentatives de connexion ;
3. `reindex_archives --missing` : indexe pour la recherche plein texte les archives qui ne le sont pas encore (instantané lorsque tout est à jour) ;
4. `bootstrap_default_admins --create-only --allow-missing` : crée les comptes privilégiés manquants. Il ne réactive pas un compte désactivé et ne réinitialise pas un mot de passe changé. Si les variables `CTECH_*` sont absentes, il écrit un avertissement et laisse l’application démarrer ;
5. gunicorn avec journal d’accès sur la sortie standard.

## 2. Variables d’environnement

| Variable | Valeur | Rôle |
|---|---|---|
| `DJANGO_ENV` | `production` | Profil de production (refuse `DEBUG`) |
| `DJANGO_DEBUG` | `False` | Debug désactivé |
| `DJANGO_SECRET_KEY` | générée par Render | Secret cryptographique |
| `DJANGO_ALLOWED_HOSTS` | `c-tech-archives.onrender.com` | Hôte public (à saisir) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://c-tech-archives.onrender.com` | Origine CSRF (à saisir) |
| `DJANGO_SESSION_COOKIE_SECURE` / `DJANGO_CSRF_COOKIE_SECURE` | `True` | Cookies HTTPS uniquement |
| `DJANGO_SECURE_SSL_REDIRECT` | `True` | Redirection HTTPS (sauf `/healthz/`) |
| `DJANGO_USE_X_FORWARDED_PROTO` | `True` | Confiance dans l’en-tête HTTPS du proxy Render |
| `DJANGO_SECURE_HSTS_SECONDS` | `0` | HSTS à activer une fois le domaine final stabilisé |
| `POSTGRES_*` | issues de `ctech-postgres-db` | Connexion à la base |
| `CTECH_STEVEN_EMAIL` / `CTECH_STEVEN_PASSWORD` | à saisir | Administrateur métier |
| `CTECH_EULOGE_EMAIL` / `CTECH_EULOGE_PASSWORD` | à saisir | Superutilisateur technique |
| `CTECH_BOOTSTRAP_RECONCILE` | `false` | Voir § 3 |
| `DJANGO_LOG_LEVEL` | `INFO` | Journaux applicatifs (`ctech.*`) |

Les mots de passe `CTECH_*` doivent passer les validateurs Django ; sinon la commande refuse le compte et l’indique dans les journaux, sans afficher la valeur.

## 3. Réaligner un compte privilégié sans shell

L’offre gratuite n’a pas de shell. Pour réinitialiser un mot de passe oublié ou réactiver un administrateur :

1. Mettre à jour `CTECH_*_PASSWORD` si besoin.
2. Passer `CTECH_BOOTSTRAP_RECONCILE` à `true`, puis redéployer.
3. Vérifier dans les journaux la ligne `Privileged accounts bootstrapped (reconcile)`.
4. Remettre `CTECH_BOOTSTRAP_RECONCILE` à `false`.

## 4. Diagnostic d’une panne

| Symptôme | Vérification | Cause probable |
|---|---|---|
| Connexion TLS ouverte mais aucune réponse | Tableau de bord Render, onglet *Events* et *Logs* | Démarrage bloqué : base indisponible ou expirée, migration en échec |
| `/healthz/` répond 503 | Journaux `ctech.health` | Base injoignable |
| Erreur 500 | Journaux `django.request` (traceback complet sur la sortie standard) | Bug applicatif |
| Connexion refusée « Trop de tentatives » | Journaux `ctech.security` (empreinte du compte, jamais l’e-mail) | Verrouillage de 15 minutes après 5 échecs |

La base PostgreSQL de l’offre gratuite de Render expire au bout d’une période limitée. Si elle a expiré, il faut en créer une nouvelle (ou passer à une offre payante), redéployer, puis recréer les comptes par le bootstrap.

## 5. Limites de l’offre gratuite

> [!WARNING]
> Le disque du service est éphémère : les documents déposés disparaissent au redémarrage ou au redéploiement. L’instance s’endort après une période d’inactivité, et le premier accès peut prendre plusieurs dizaines de secondes. Cette configuration convient à une démonstration avec des données synthétiques, pas à la conservation d’archives réelles. Pour un usage réel, il faut un disque persistant Render ou un stockage objet privé.
