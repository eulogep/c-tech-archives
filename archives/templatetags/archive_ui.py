"""Balises de présentation partagées par les gabarits de l’interface."""

from django import template
from django.utils.html import format_html

from archives.presentation import BRAND_SEAL_SEED, FILE_KIND_LABELS, file_kind, render_seal


register = template.Library()


@register.simple_tag
def seal(reference, size=48, label="", css_class=""):
    """Sceau génératif d’une archive, dérivé de sa référence."""
    return render_seal(str(reference), size=int(size), label=label, css_class=css_class)


@register.simple_tag
def brand_seal(size=48, css_class=""):
    """Sceau de la marque C-Tech Archives."""
    return render_seal(BRAND_SEAL_SEED, size=int(size), css_class=css_class)


@register.filter
def kind_of(file_name):
    return file_kind(str(file_name or ""))


@register.filter
def kind_label(kind):
    return FILE_KIND_LABELS.get(kind, FILE_KIND_LABELS["file"])


@register.filter
def initials(value):
    """Deux initiales lisibles à partir d’un nom complet ou d’un e-mail."""
    text = str(value or "").split("@")[0]
    parts = [part for part in text.replace(".", " ").replace("-", " ").split() if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


@register.filter
def tone_of(value):
    """Teinte stable (0–11) pour colorer un avatar sans image, via une classe CSS."""
    return sum(ord(character) for character in str(value or "")) * 7 % 12


@register.simple_tag
def icon(name, css_class=""):
    """Icône du sprite SVG interne (décorative, masquée aux lecteurs d’écran)."""
    return format_html(
        '<svg class="icon{}" aria-hidden="true" focusable="false"><use href="#i-{}"></use></svg>',
        f" {css_class}" if css_class else "",
        name,
    )
