"""Vues techniques transverses."""

import logging

from django.db import connection
from django.db.utils import DatabaseError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


logger = logging.getLogger("ctech.health")


@never_cache
@require_GET
def healthz(request):
    """Sonde de santé : vérifie la base sans exposer de détail technique.

    Une page de connexion qui répond 200 n’est pas un signal fiable : elle
    s’affiche même lorsque la base n’est pas migrée.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        logger.exception("Health check failed: database unavailable")
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
