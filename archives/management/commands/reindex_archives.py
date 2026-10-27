"""(Ré)indexe le contenu des archives pour la recherche plein texte.

Sans option, la commande relit tous les fichiers pris en charge et recalcule
tous les vecteurs. Avec ``--missing``, elle ne traite que les archives jamais
indexées : c’est le mode utilisé au démarrage sur Render, presque instantané
lorsque tout est à jour.
"""

from django.core.management.base import BaseCommand

from archives.models import Archive
from archives.search import update_search_document
from archives.text_extraction import extract_text, supports


class Command(BaseCommand):
    help = "Extrait le texte des documents et met à jour l’index de recherche plein texte."

    def add_arguments(self, parser):
        parser.add_argument(
            "--missing",
            action="store_true",
            help="Ne traiter que les archives sans index de recherche.",
        )

    def handle(self, *args, **options):
        queryset = Archive.objects.order_by("pk")
        if options["missing"]:
            queryset = queryset.filter(search_document__isnull=True)

        indexed = extracted = unreadable = 0
        for archive in queryset.iterator(chunk_size=200):
            if archive.file and supports(archive.file.name):
                try:
                    with archive.file.open("rb") as handle:
                        text = extract_text(handle, archive.file.name)
                except OSError:
                    text = ""
                    unreadable += 1
                if text != archive.content_text:
                    Archive.objects.filter(pk=archive.pk).update(content_text=text)
                if text:
                    extracted += 1
            update_search_document(archive.pk)
            indexed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Search index updated: {indexed} archives, {extracted} with extracted text, "
                f"{unreadable} unreadable files."
            )
        )
