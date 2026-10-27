"""Exports CSV communs : diffusion en flux et neutralisation des formules."""

import csv

from django.http import StreamingHttpResponse
from django.utils import timezone


# Préfixes interprétés comme formules par les tableurs (injection CSV).
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value) -> str:
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(FORMULA_PREFIXES) else text


class _Echo:
    def write(self, value):
        return value


def csv_response(filename_prefix: str, header, rows) -> StreamingHttpResponse:
    """Réponse CSV (UTF-8 avec BOM, séparateur « ; » pour les tableurs français)."""
    writer = csv.writer(_Echo(), delimiter=";")

    def stream():
        yield "﻿"
        yield writer.writerow(header)
        for row in rows:
            yield writer.writerow(row)

    filename = f"{filename_prefix}-{timezone.localdate():%Y%m%d}.csv"
    response = StreamingHttpResponse(stream(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "private, no-store"
    return response
