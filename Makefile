# Raccourcis de développement. Prérequis : Python 3.12+, Docker, un fichier .env.
PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip

.PHONY: help setup db migrate run test check seed reindex audit-deps static

help: ## Affiche les commandes disponibles
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-12s %s\n", $$1, $$2}'

setup: ## Crée le venv et installe les versions figées
	python3 -m venv .venv
	$(PIP) install -r requirements.txt -c constraints.txt

db: ## Démarre PostgreSQL en local (docker compose)
	docker compose up -d --wait postgres

migrate: ## Applique les migrations
	$(PYTHON) manage.py migrate

run: ## Lance le serveur de développement sur http://127.0.0.1:8000
	$(PYTHON) manage.py runserver

test: ## Lance toute la suite de tests
	$(PYTHON) manage.py test --noinput

check: ## Contrôles Django et dérive des migrations
	$(PYTHON) manage.py check
	$(PYTHON) manage.py makemigrations --check --dry-run

seed: ## Jeu de démonstration (CTECH_DEMO_PASSWORD requis, jamais en production)
	$(PYTHON) manage.py seed_demo

reindex: ## Indexe le contenu des documents pour la recherche plein texte
	$(PYTHON) manage.py reindex_archives

static: ## Collecte et compresse les fichiers statiques
	$(PYTHON) manage.py collectstatic --noinput

audit-deps: ## Recherche de vulnérabilités connues dans les dépendances figées
	pipx run pip-audit -r constraints.txt
