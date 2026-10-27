"""Aides de présentation des archives : familles de fichiers et sceaux génératifs.

Le sceau est dérivé de la *référence* de l’archive, jamais de l’empreinte du
fichier : il identifie visuellement un dossier sans rien révéler de son contenu.
L’algorithme est reproduit à l’identique dans ``static/js/app.js`` pour
l’aperçu en direct du formulaire.
"""

from __future__ import annotations

import math
from hashlib import sha256
from pathlib import Path

from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe


FILE_KINDS = {
    ".pdf": "pdf",
    ".doc": "doc",
    ".docx": "doc",
    ".xls": "sheet",
    ".xlsx": "sheet",
    ".txt": "text",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
}
FILE_KIND_LABELS = {
    "pdf": "Document PDF",
    "doc": "Document Word",
    "sheet": "Classeur Excel",
    "text": "Texte brut",
    "image": "Image",
    "file": "Fichier",
}
PREVIEWABLE_KINDS = frozenset({"image", "text"})
# Graine choisie pour un sceau de marque indigo et violet, entièrement rempli.
BRAND_SEAL_SEED = "C-Tech Archives 2790"

# (rayon intérieur, rayon extérieur, nombre de segments) — symétrie miroir.
SEAL_RINGS = ((13, 22, 6), (24, 33, 12), (35, 43.5, 18))
SEAL_OPACITIES = (0, 0.38, 0.66, 0.95)
SEAL_TICKS = 48


def svg_number(value) -> str:
    """Nombre pour un attribut SVG : point décimal, jamais localisé (« 187,5 »)."""
    return f"{value:.2f}".rstrip("0").rstrip(".") or "0"


def file_kind(name: str) -> str:
    return FILE_KINDS.get(Path(name or "").suffix.lower(), "file")


def _point(radius: float, angle: float) -> tuple[float, float]:
    radians = math.radians(angle)
    return 50 + radius * math.sin(radians), 50 - radius * math.cos(radians)


def _sector_path(inner: float, outer: float, start: float, end: float) -> str:
    large = 1 if end - start > 180 else 0
    x1, y1 = _point(outer, start)
    x2, y2 = _point(outer, end)
    x3, y3 = _point(inner, end)
    x4, y4 = _point(inner, start)
    return (
        f"M{x1:.2f} {y1:.2f}A{outer} {outer} 0 {large} 1 {x2:.2f} {y2:.2f}"
        f"L{x3:.2f} {y3:.2f}A{inner} {inner} 0 {large} 0 {x4:.2f} {y4:.2f}Z"
    )


def _bits(digest: bytes, start_byte: int):
    for byte in digest[start_byte:]:
        for shift in (6, 4, 2, 0):
            yield (byte >> shift) & 0b11


def seal_geometry(reference: str) -> dict:
    """Calcule couleurs et segments du sceau d’une référence."""
    digest = sha256((reference or "").strip().encode("utf-8")).digest()
    hue = digest[0] * 360 // 256
    accent = (hue + 40 + digest[1] % 100) % 360
    rotation = digest[7] % 30
    levels = _bits(digest, 2)
    segments = []
    for ring_index, (inner, outer, count) in enumerate(SEAL_RINGS):
        span = 360 / count
        half = [next(levels) for _ in range(count // 2)]
        values = half + half[::-1]
        ring_hue = accent if ring_index % 2 == 0 else hue
        for index, level in enumerate(values):
            if not level:
                continue
            start = rotation + index * span + 2.2
            end = rotation + (index + 1) * span - 2.2
            segments.append(
                {
                    "d": _sector_path(inner, outer, start, end),
                    "fill": f"hsl({ring_hue}, 78%, 66%)",
                    "opacity": SEAL_OPACITIES[level],
                }
            )
    ticks = []
    for index in range(SEAL_TICKS):
        angle = index * 360 / SEAL_TICKS
        x1, y1 = _point(45.6, angle)
        x2, y2 = _point(47.6 if index % 4 else 48.6, angle)
        ticks.append(f"M{x1:.2f} {y1:.2f}L{x2:.2f} {y2:.2f}")
    return {
        "hue": hue,
        "accent": accent,
        "segments": segments,
        "ticks": "".join(ticks),
    }


def render_seal(reference: str, *, size: int = 48, label: str = "", css_class: str = "") -> str:
    """Retourne le SVG du sceau ; décoratif sauf si un libellé est fourni."""
    geometry = seal_geometry(reference)
    accessibility = (
        format_html('role="img" aria-label="{}"', label) if label else mark_safe('aria-hidden="true"')
    )
    paths = format_html_join(
        "",
        '<path d="{}" fill="{}" fill-opacity="{}"/>',
        ((segment["d"], segment["fill"], segment["opacity"]) for segment in geometry["segments"]),
    )
    return format_html(
        '<svg class="seal {css}" viewBox="0 0 100 100" width="{size}" height="{size}" {a11y} focusable="false">'
        '<circle cx="50" cy="50" r="49" fill="hsl({hue}, 42%, 15%)"/>'
        '<circle cx="50" cy="50" r="44.6" fill="none" stroke="hsl({hue}, 70%, 70%)" stroke-opacity=".35" stroke-width=".8"/>'
        '<path d="{ticks}" stroke="hsl({hue}, 75%, 75%)" stroke-opacity=".55" stroke-width=".9" stroke-linecap="round"/>'
        "{paths}"
        '<circle cx="50" cy="50" r="9" fill="hsl({accent}, 85%, 72%)"/>'
        '<circle cx="50" cy="50" r="4.2" fill="hsl({hue}, 42%, 15%)"/>'
        "</svg>",
        css=css_class,
        size=size,
        a11y=accessibility,
        hue=geometry["hue"],
        accent=geometry["accent"],
        ticks=geometry["ticks"],
        paths=paths,
    )
