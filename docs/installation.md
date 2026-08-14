# Installation et exécution locale

Ce guide permet de préparer C-Tech Archives depuis un clone propre avec PostgreSQL. Il ne décrit ni Docker, ni service cloud, ni procédure de déploiement qui ne sont pas présents dans le dépôt.

## Prérequis

| Composant | Usage dans le projet |
|---|---|
| Python 3.12 ou compatible avec les contraintes du projet | Exécution de Django et des tests |
| PostgreSQL | Base relationnelle applicative |
| Git | Clonage du dépôt et suivi des versions |
| Environnement virtuel Python | Isolation des dépendances |

Les dépendances directes sont définies dans `requirements.txt` : Django 5.1.x, `psycopg[binary]` 3.2.x, `python-dotenv` 1.x et Pillow 10–11.x.

## Clone et environnement Python

```bash
git clone https://github.com/eulogep/c-tech-archives.git
cd c-tech-archives
python -m venv .venv
```

Sous Linux ou macOS, activez l’environnement avec :

```bash
source .venv/bin/activate
```

Sous Windows PowerShell, utilisez :

```powershell
.\.venv\Scripts\Activate.ps1
```

Installez ensuite les dépendances déclarées :

```bash
pip install -r requirements.txt
```

## Configuration d’environnement

Copiez l’exemple versionné et adaptez-le localement. Le fichier `.env` contient des secrets et ne doit pas être ajouté à Git.

```bash
cp .env.example .env
```

Sous Windows, créez une copie manuelle de `.env.example` nommée `.env`. Les valeurs de démonstration doivent être remplacées par un secret Django et un mot de passe PostgreSQL propres à l’environnement local.

## PostgreSQL

Créez une base et un rôle applicatif local correspondant aux variables configurées dans `.env`. Les commandes exactes dépendent de votre installation PostgreSQL ; un exemple de création locale est :

```sql
CREATE USER c_tech_app WITH PASSWORD 'choisir-un-mot-de-passe-local-fort';
CREATE DATABASE c_tech_archives OWNER c_tech_app;
```

Ne réutilisez pas cet exemple de mot de passe ; il est fourni uniquement pour illustrer la commande. Vérifiez que `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` et `POSTGRES_PORT` de `.env` correspondent à votre instance.

## Migrations, comptes privilégiés et lancement

Appliquez d’abord le schéma Django :

```bash
python manage.py migrate
```

Les comptes privilégiés C-Tech peuvent ensuite être initialisés ou réconciliés explicitement avec la commande suivante :

```bash
python manage.py bootstrap_default_admins
```

Cette commande lit uniquement `CTECH_STEVEN_EMAIL`, `CTECH_STEVEN_PASSWORD`, `CTECH_EULOGE_EMAIL` et `CTECH_EULOGE_PASSWORD` depuis `.env` ou l’environnement d’exécution. Elle ne crée aucun utilisateur au démarrage de l’application, ne révèle aucun mot de passe et peut être relancée sans créer de doublon. Le compte métier Administrateur et les privilèges techniques Django restent distincts : le bootstrap configure un administrateur métier sans droits Django illimités et un compte technique superutilisateur séparé.

Après avoir configuré les variables d’environnement requises, démarrez l’application :

```bash
python manage.py runserver
```

L’application est alors accessible localement à l’adresse affichée par Django, habituellement `http://127.0.0.1:8000/`. Le mode développement conserve `DEBUG=True`, des cookies secure désactivés et les hôtes locaux `localhost,127.0.0.1` ; ces réglages ne conviennent pas à une production HTTPS.

## Création de données de démonstration

La démonstration doit employer exclusivement des données synthétiques. Créez localement des rôles métier et référentiels tels que **Service Direction Administrative**, **Service RH Démo**, **Catégorie Contrats Démo** et **Type Rapport Démo** via l’administration Django ou les écrans autorisés. Ne commitez ni comptes, ni mots de passe, ni archives réelles C-Tech.

## Tests et contrôles de configuration

Avant une démonstration ou une modification, exécutez les contrôles suivants :

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py test
```

La baseline actuelle contient **263 tests**. Le contrôle de déploiement local affiche cinq warnings attendus lorsque le développement conserve HTTP et `DEBUG=True` :

```bash
python manage.py check --deploy
```

Pour une simulation de production, fournissez un hôte explicite, désactivez DEBUG et activez les paramètres HTTPS/cookies/HSTS documentés dans `.env.example`. `DJANGO_ALLOWED_HOSTS=*` est refusé hors développement.

## Références utiles

| Besoin | Document |
|---|---|
| Variables d’environnement et production | [`environment.md`](environment.md) |
| Architecture finale | [`architecture-final.md`](architecture-final.md) |
| Guide de démonstration utilisateur | [`user-guide.md`](user-guide.md) |
| Matrice de tests | [`final-test-matrix.md`](final-test-matrix.md) |
| Limites de sécurité | [`security-review.md`](security-review.md) |
