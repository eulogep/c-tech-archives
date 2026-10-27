"""Recherche plein texte PostgreSQL : pondération, insensibilité aux accents, extraits.

Le vecteur ``search_document`` est calculé à partir de textes déjà normalisés
(minuscules, sans accents) avec la configuration ``french`` : « sécurité »,
« securite » et « Sécurités » se retrouvent. Les poids distinguent la
référence et le titre (A), la description et le classement (B) et le contenu
extrait du fichier (C). La recherche par sous-chaîne d’origine reste en
repli pour les références partielles comme « CT-2026-00 ».
"""

from __future__ import annotations

import re
import unicodedata

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import F, Q, TextField, Value
from django.db.models.functions import Coalesce

from .models import Archive


SNIPPET_RADIUS = 90
_TOKEN = re.compile(r"[\w’']{3,}", re.UNICODE)
_EXCLUDED_TOKENS = {"and", "or", "not", "ou", "et"}


def normalize(text: str) -> str:
    """Minuscules sans diacritiques (é → e, Œ → œ conservé)."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()


def build_query(raw_query: str) -> SearchQuery:
    return SearchQuery(normalize(raw_query), config="french", search_type="websearch")


def _vector(text: str, weight: str) -> SearchVector:
    return SearchVector(Value(normalize(text), output_field=TextField()), config="french", weight=weight)


def update_search_document(archive_id: int) -> None:
    """Recalcule le vecteur d’une archive après création, modification ou extraction."""
    archive = (
        Archive.objects.select_related("service", "category", "document_type")
        .only(
            "reference",
            "title",
            "description",
            "content_text",
            "service__name",
            "category__name",
            "document_type__name",
        )
        .get(pk=archive_id)
    )
    classification = " ".join(
        (
            archive.description,
            archive.service.name,
            archive.category.name,
            archive.document_type.name,
        )
    )
    vector = (
        _vector(f"{archive.reference} {archive.title}", "A")
        + _vector(classification, "B")
        + _vector(archive.content_text, "C")
    )
    Archive.objects.filter(pk=archive_id).update(search_document=vector)


def apply_text_search(queryset, raw_query: str):
    """Filtre un QuerySet *déjà restreint par le RBAC* et annote la pertinence."""
    query = build_query(raw_query)
    return queryset.filter(
        Q(search_document=query)
        | Q(reference__icontains=raw_query)
        | Q(title__icontains=raw_query)
        | Q(description__icontains=raw_query)
    ).annotate(rank=Coalesce(SearchRank(F("search_document"), query), Value(0.0)))


def _query_tokens(raw_query: str) -> list[str]:
    tokens = []
    for token in _TOKEN.findall(normalize(raw_query)):
        if token in _EXCLUDED_TOKENS:
            continue
        # Racine grossière pour retrouver « contrat » à partir de « contrats ».
        tokens.append(token[: max(4, len(token) - 2)])
    return tokens


def content_snippet(content: str, raw_query: str) -> dict | None:
    """Extrait du contenu autour du premier terme trouvé, à échapper au rendu.

    La correspondance se fait sur le texte normalisé, mais l’extrait renvoyé
    est découpé dans le texte d’origine : les accents sont conservés.
    """
    if not content or not raw_query:
        return None
    normalized_chars = []
    origin = []
    for index, char in enumerate(content):
        for produced in normalize(char):
            normalized_chars.append(produced)
            origin.append(index)
    normalized = "".join(normalized_chars)
    for token in _query_tokens(raw_query):
        position = normalized.find(token)
        if position < 0:
            continue
        start = origin[position]
        end = origin[min(position + len(token), len(origin) - 1)]
        while end < len(content) and (content[end].isalnum() or content[end] in "’'"):
            end += 1
        before_start = max(0, start - SNIPPET_RADIUS)
        after_end = min(len(content), end + SNIPPET_RADIUS)
        return {
            "before": ("…" if before_start else "") + " ".join(content[before_start:start].split()) + " ",
            "match": content[start:end],
            "after": " " + " ".join(content[end:after_end].split()) + ("…" if after_end < len(content) else ""),
        }
    return None
