"""Extraction du texte des documents pour la recherche plein texte.

Chaque extracteur est borné (taille lue, pages, caractères) et ne lève jamais :
un document illisible reste archivable, il n’est simplement pas indexé. Les
fichiers Office sont lus comme des archives ZIP, sans analyse XML ni exécution
de macro ; les PDF passent par pypdf en mode non strict.
"""

from __future__ import annotations

import html
import logging
import re
import zipfile
from io import BytesIO
from pathlib import Path


logger = logging.getLogger("ctech.search")

MAX_TEXT_CHARS = 200_000
MAX_SOURCE_BYTES = 12 * 1024 * 1024
MAX_XML_BYTES = 8 * 1024 * 1024
MAX_PDF_PAGES = 60

_WORD_TEXT = re.compile(rb"<w:t(?:\s[^>]*)?>([^<]*)</w:t>")
_WORD_BREAK = re.compile(rb"</w:p>")
_SHEET_TEXT = re.compile(rb"<t(?:\s[^>]*)?>([^<]*)</t>")
_WHITESPACE = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINES = re.compile(r"\n{3,}")


def _clean(text: str) -> str:
    text = text.replace("\x00", " ")
    text = _WHITESPACE.sub(" ", text)
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()[:MAX_TEXT_CHARS]


def _read_member(archive: zipfile.ZipFile, name: str) -> bytes:
    """Lit un membre ZIP sans dépasser la limite, même s’il ment sur sa taille."""
    try:
        with archive.open(name) as member:
            return member.read(MAX_XML_BYTES)
    except KeyError:
        return b""


def _from_text(data: bytes) -> str:
    for encoding in ("utf-8", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _from_docx(data: bytes) -> str:
    with zipfile.ZipFile(BytesIO(data)) as archive:
        xml = _read_member(archive, "word/document.xml")
    xml = _WORD_BREAK.sub(b"</w:p>\n", xml)
    parts = []
    for line in xml.split(b"\n"):
        words = [html.unescape(chunk.decode("utf-8", "replace")) for chunk in _WORD_TEXT.findall(line)]
        if words:
            parts.append("".join(words))
    return "\n".join(parts)


def _from_xlsx(data: bytes) -> str:
    with zipfile.ZipFile(BytesIO(data)) as archive:
        xml = _read_member(archive, "xl/sharedStrings.xml")
    return "\n".join(
        html.unescape(chunk.decode("utf-8", "replace")) for chunk in _SHEET_TEXT.findall(xml)
    )


def _from_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data), strict=False)
    pages = []
    collected = 0
    for page in reader.pages[:MAX_PDF_PAGES]:
        text = page.extract_text() or ""
        pages.append(text)
        collected += len(text)
        if collected >= MAX_TEXT_CHARS:
            break
    return "\n".join(pages)


EXTRACTORS = {
    ".txt": _from_text,
    ".docx": _from_docx,
    ".xlsx": _from_xlsx,
    ".pdf": _from_pdf,
}


def supports(name: str) -> bool:
    return Path(name or "").suffix.lower() in EXTRACTORS


def extract_text(file_obj, name: str) -> str:
    """Texte indexable d’un fichier, ou chaîne vide si le format n’est pas pris en charge.

    Les images et les anciens formats binaires (.doc, .xls) ne sont pas lus :
    leur contenu nécessiterait une OCR ou un convertisseur dédié.
    """
    extractor = EXTRACTORS.get(Path(name or "").suffix.lower())
    if extractor is None:
        return ""
    try:
        position = file_obj.tell()
    except (AttributeError, OSError):
        position = None
    try:
        file_obj.seek(0)
        data = file_obj.read(MAX_SOURCE_BYTES + 1)
        if len(data) > MAX_SOURCE_BYTES:
            data = data[:MAX_SOURCE_BYTES]
        return _clean(extractor(data))
    except Exception:  # noqa: BLE001 — un document illisible ne doit pas bloquer l’archivage.
        logger.warning("Text extraction failed for a %s document", Path(name).suffix.lower())
        return ""
    finally:
        if position is not None:
            try:
                file_obj.seek(position)
            except (AttributeError, OSError):
                pass
