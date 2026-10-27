"""Tests des améliorations livrées depuis la feuille de route participative."""

import zipfile
from datetime import timedelta
from hashlib import sha256
from io import BytesIO, StringIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from archives.forms import ArchiveForm
from archives.management.commands.seed_demo import _pdf_bytes
from archives.models import (
    Archive,
    ArchiveStatus,
    Category,
    ConfidentialityLevel,
    DocumentType,
    Service,
)
from archives.retention import deadline_overview, retention_state
from archives.search import apply_text_search, content_snippet, normalize, update_search_document
from archives.text_extraction import extract_text


PASSWORD = "Synthetic-Roadmap-Password-2026!"


def docx_bytes(paragraphs):
    body = "".join(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs)
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "word/document.xml",
            f'<w:document xmlns:w="urn:w"><w:body>{body}</w:body></w:document>',
        )
    return buffer.getvalue()


def xlsx_bytes(cells):
    strings = "".join(f"<si><t>{text}</t></si>" for text in cells)
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("xl/sharedStrings.xml", f"<sst>{strings}</sst>")
    return buffer.getvalue()


class RoadmapTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.private_media = TemporaryDirectory()
        self.override = override_settings(PRIVATE_MEDIA_ROOT=self.private_media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.private_media.cleanup)
        users = get_user_model().objects
        self.admin = users.create_user(
            username="road-admin@example.test", email="road-admin@example.test",
            password=PASSWORD, role=Role.ADMINISTRATEUR,
        )
        self.agent = users.create_user(
            username="road-agent@example.test", email="road-agent@example.test",
            password=PASSWORD, role=Role.AGENT_ARCHIVES,
        )
        self.consultant = users.create_user(
            username="road-consultant@example.test", email="road-consultant@example.test",
            password=PASSWORD, role=Role.CONSULTANT,
        )
        self.service = Service.objects.create(name="Service conservation")
        self.category = Category.objects.create(name="Catégorie conservation")
        self.document_type = DocumentType.objects.create(name="Type conservation")
        self.today = timezone.localdate()

    def archive(self, reference, level=ConfidentialityLevel.PUBLIC, content=None, extension="txt", **extra):
        values = {
            "reference": reference,
            "title": f"Titre {reference}",
            "category": self.category,
            "document_type": self.document_type,
            "service": self.service,
            "uploaded_by": self.admin,
            "status": ArchiveStatus.ACTIVE,
            "confidentiality_level": level,
        }
        if content is not None:
            values["file"] = SimpleUploadedFile(f"{reference}.{extension}", content)
            values["file_size"] = len(content)
            values["checksum"] = sha256(content).hexdigest()
        values.update(extra)
        archive = Archive.objects.create(**values)
        if content is not None:
            with archive.file.open("rb") as handle:
                archive.content_text = extract_text(handle, archive.file.name)
            archive.save(update_fields=["content_text"])
        update_search_document(archive.pk)
        return archive


class RetentionStateTests(RoadmapTestCase):
    def state(self, **dates):
        archive = Archive(document_date=self.today - timedelta(days=100), **dates)
        return retention_state(archive, self.today)

    def test_states_cover_the_whole_lifecycle(self):
        cases = {
            "alert": {"retention_until": self.today - timedelta(days=1)},
            "warning": {"review_date": self.today - timedelta(days=3), "retention_until": self.today + timedelta(days=900)},
            "info": {"review_date": self.today + timedelta(days=10)},
            "valid": {"retention_until": self.today + timedelta(days=400)},
            "unknown": {},
        }
        for tone, dates in cases.items():
            with self.subTest(tone=tone):
                self.assertEqual(self.state(**dates).tone, tone)

    def test_retention_soon_and_progress(self):
        state = self.state(retention_until=self.today + timedelta(days=20))

        self.assertEqual(state.label, "Fin de conservation proche")
        self.assertEqual(state.progress, 83)

    def test_form_rejects_incoherent_dates(self):
        form = ArchiveForm(
            data={
                "reference": "CT-RET-FORM",
                "title": "Dates incohérentes",
                "category": self.category.pk,
                "document_type": self.document_type.pk,
                "service": self.service.pk,
                "status": ArchiveStatus.ACTIVE,
                "confidentiality_level": ConfidentialityLevel.PUBLIC,
                "document_date": "2026-05-01",
                "retention_until": "2026-01-01",
                "review_date": "2027-01-01",
            },
            user=self.admin,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("retention_until", form.errors)

        form = ArchiveForm(
            data={**form.data, "retention_until": "2026-12-01"},
            user=self.admin,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("review_date", form.errors)


class RetentionViewsTests(RoadmapTestCase):
    def setUp(self):
        super().setUp()
        self.public_overdue = self.archive("CT-RET-PUB", retention_until=self.today - timedelta(days=5))
        self.confidential_overdue = self.archive(
            "CT-RET-CONF", ConfidentialityLevel.CONFIDENTIAL, retention_until=self.today - timedelta(days=5)
        )
        self.soon = self.archive("CT-RET-SOON", review_date=self.today + timedelta(days=12))
        self.later = self.archive("CT-RET-LATER", retention_until=self.today + timedelta(days=2000))

    def references(self, user, **params):
        self.client.force_login(user)
        response = self.client.get(reverse("archives:list"), params)
        return {archive.reference for archive in response.context["archives"]}

    def test_deadline_filter_respects_rbac(self):
        self.assertEqual(self.references(self.consultant, deadline="overdue"), {"CT-RET-PUB"})
        self.assertEqual(self.references(self.admin, deadline="overdue"), {"CT-RET-PUB", "CT-RET-CONF"})
        self.assertEqual(self.references(self.admin, deadline="next_30"), {"CT-RET-SOON"})
        self.assertNotIn("CT-RET-LATER", self.references(self.admin, deadline="next_90"))

    def test_dashboard_deadlines_only_count_the_visible_scope(self):
        consultant = deadline_overview(
            Archive.objects.filter(confidentiality_level=ConfidentialityLevel.PUBLIC), self.today
        )
        self.client.force_login(self.consultant)
        response = self.client.get("/")

        self.assertEqual(response.context["deadlines"]["overdue"], consultant["overdue"])
        self.assertEqual(response.context["deadlines"]["overdue"], 1)
        self.assertContains(response, "Échéances de conservation")
        self.assertNotContains(response, "CT-RET-CONF")
        self.assertContains(response, "CT-RET-SOON")

    def test_detail_shows_the_retention_section(self):
        self.client.force_login(self.agent)

        response = self.client.get(reverse("archives:detail", args=[self.public_overdue.pk]))

        self.assertContains(response, "E. Conservation")
        self.assertContains(response, "Conservation échue")

    def test_sort_by_retention_date(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("archives:list"), {"sort": "retention"})
        references = [a.reference for a in response.context["archives"]]

        # Échéances croissantes (égalité départagée par création), dossiers sans date en dernier.
        self.assertEqual(references, ["CT-RET-PUB", "CT-RET-CONF", "CT-RET-LATER", "CT-RET-SOON"])


class TextExtractionTests(TestCase):
    def test_supported_formats_are_extracted(self):
        cases = {
            "note.txt": "Procédure d’évacuation du bâtiment".encode(),
            "rapport.docx": docx_bytes(["Rapport annuel", "Bilan d’activité très positif"]),
            "budget.xlsx": xlsx_bytes(["Ligne budgétaire", "Maintenance"]),
            "contrat.pdf": _pdf_bytes("Contrat de maintenance"),
        }
        expected = {
            "note.txt": "évacuation",
            "rapport.docx": "Bilan d’activité",
            "budget.xlsx": "Maintenance",
            "contrat.pdf": "Contrat de maintenance",
        }
        for name, content in cases.items():
            with self.subTest(name=name):
                self.assertIn(expected[name], extract_text(BytesIO(content), name))

    def test_unsupported_or_corrupt_files_never_raise(self):
        self.assertEqual(extract_text(BytesIO(b"\x89PNG\r\n\x1a\n"), "image.png"), "")
        self.assertEqual(extract_text(BytesIO(b"%PDF-1.4 broken"), "broken.pdf"), "")
        self.assertEqual(extract_text(BytesIO(b"not a zip"), "broken.docx"), "")

    def test_extracted_text_is_bounded(self):
        from archives.text_extraction import MAX_TEXT_CHARS

        text = extract_text(BytesIO(b"a " * MAX_TEXT_CHARS), "long.txt")

        self.assertLessEqual(len(text), MAX_TEXT_CHARS)

    def test_normalization_removes_accents_and_case(self):
        self.assertEqual(normalize("Sécurité ÉCHÉANCE"), "securite echeance")


class FullTextSearchTests(RoadmapTestCase):
    def setUp(self):
        super().setUp()
        self.public = self.archive("CT-FTS-PUB", content="Procédure d’évacuation et consignes de sécurité incendie.".encode())
        self.confidential = self.archive(
            "CT-FTS-CONF",
            ConfidentialityLevel.CONFIDENTIAL,
            content="Plan de sécurité confidentiel et codes d’accès.".encode(),
        )

    def search(self, user, query, **params):
        self.client.force_login(user)
        return self.client.get(reverse("archives:list"), {"q": query, **params})

    def test_document_content_is_searchable_without_accents_or_exact_forms(self):
        for query in ("evacuation", "procedures", "SECURITE incendie", '"consignes de sécurité"'):
            with self.subTest(query=query):
                references = {a.reference for a in self.search(self.admin, query).context["archives"]}
                self.assertIn("CT-FTS-PUB", references)

    def test_content_search_respects_confidentiality(self):
        consultant = {a.reference for a in self.search(self.consultant, "sécurité").context["archives"]}
        admin = {a.reference for a in self.search(self.admin, "sécurité").context["archives"]}

        self.assertEqual(consultant, {"CT-FTS-PUB"})
        self.assertEqual(admin, {"CT-FTS-PUB", "CT-FTS-CONF"})
        self.client.force_login(self.consultant)
        quick = self.client.get(reverse("archives:quick_search"), {"q": "codes d’accès"}).json()
        self.assertEqual(quick["results"], [])

    def test_results_show_an_escaped_highlighted_snippet(self):
        hostile = self.archive("CT-FTS-XSS", content=b"<script>alert(1)</script> rapport sensible")

        response = self.search(self.admin, "sensible")

        self.assertContains(response, "<mark>sensible</mark>", html=False)
        self.assertContains(response, "&lt;script&gt;", html=False)
        self.assertNotContains(response, "<script>alert(1)</script>", html=False)
        self.assertTrue(any(a.pk == hostile.pk for a in response.context["archives"]))

    def test_relevance_is_the_default_order_when_searching(self):
        response = self.search(self.admin, "évacuation")

        self.assertEqual(response.context["sort"], "relevance")
        self.assertEqual(self.search(self.admin, "évacuation", sort="oldest").context["sort"], "oldest")

    def test_created_archive_is_indexed_and_reindexed_on_update(self):
        self.client.force_login(self.agent)
        self.client.post(
            reverse("archives:create"),
            {
                "reference": "CT-FTS-NEW",
                "title": "Nouvelle pièce",
                "category": self.category.pk,
                "document_type": self.document_type.pk,
                "service": self.service.pk,
                "status": ArchiveStatus.ACTIVE,
                "confidentiality_level": ConfidentialityLevel.PUBLIC,
                "file": SimpleUploadedFile("memo.txt", "Inventaire des extincteurs".encode(), content_type="text/plain"),
            },
        )
        archive = Archive.objects.get(reference="CT-FTS-NEW")
        self.assertIn("extincteurs", archive.content_text)
        self.assertEqual(apply_text_search(Archive.objects.all(), "extincteur").get().pk, archive.pk)

        self.client.post(
            reverse("archives:update", args=[archive.pk]),
            {
                "reference": "CT-FTS-NEW",
                "title": "Registre de maintenance",
                "category": self.category.pk,
                "document_type": self.document_type.pk,
                "service": self.service.pk,
                "status": ArchiveStatus.ACTIVE,
                "confidentiality_level": ConfidentialityLevel.PUBLIC,
            },
        )
        self.assertTrue(apply_text_search(Archive.objects.all(), "registre").filter(pk=archive.pk).exists())

    def test_reindex_command_indexes_missing_archives(self):
        Archive.objects.update(search_document=None, content_text="")
        output = StringIO()

        call_command("reindex_archives", "--missing", stdout=output)

        self.assertIn("2 archives, 2 with extracted text", output.getvalue())
        self.assertFalse(Archive.objects.filter(search_document__isnull=True).exists())
        self.assertIn("évacuation", Archive.objects.get(pk=self.public.pk).content_text)

    def test_snippet_keeps_original_accents(self):
        snippet = content_snippet("Le dossier précise l’échéance de révision.", "echeance")

        self.assertEqual(snippet["match"], "échéance")
