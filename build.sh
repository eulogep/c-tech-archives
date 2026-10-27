#!/usr/bin/env bash
# Arrêt immédiat en cas d'erreur
set -o errexit

pip install -r requirements.txt -c constraints.txt
python manage.py collectstatic --noinput
