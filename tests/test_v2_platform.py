"""Tests de la version 2 : interface « Sceau », exploitation et durcissements."""

import csv
import os
from hashlib import sha256
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import Role
from archives.models import (
    Archive,
    ArchiveStatus,
    Category,
    ConfidentialityLevel,
    DocumentType,
    Service,
)
from archives.presentation import render_seal, seal_geometry, svg_number
from audit.models import AuditAction, AuditLog


PASSWORD = "Synthetic-V2-Password-2026!"


def png_bytes():
    buffer = BytesIO()
    Image.new("RGB", (4, 4), (90, 80, 200)).save(buffer, format="PNG")
    return buffer.getvalue()


class PlatformTestCase(TestCase):
    """Comptes des trois rôles, référentiels et stockage privé isolé."""

    def setUp(self):
        cache.clear()
        self.private_media = TemporaryDirectory()
        self.settings_override = override_settings(PRIVATE_MEDIA_ROOT=self.private_media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.private_media.cleanup)

        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username="v2-admin@example.test",
            email="v2-admin@example.test",
            password=PASSWORD,
            first_name="Ada",
            last_name="Admin",
            role=Role.ADMINISTRATEUR,
        )
        self.agent = user_model.objects.create_user(
            username="v2-agent@example.test",
            email="v2-agent@example.test",
            password=PASSWORD,
            role=Role.AGENT_ARCHIVES,
        )
        self.consultant = user_model.objects.create_user(
            username="v2-consultant@example.test",
            email="v2-consultant@example.test",
            password=PASSWORD,
            role=Role.CONSULTANT,
        )
        self.service = Service.objects.create(name="Service V2")
        self.category = Category.objects.create(name="Catégorie V2")
        self.document_type = DocumentType.objects.create(name="Type V2")

    def create_archive(self, reference, level=ConfidentialityLevel.PUBLIC, content=None, extension="pdf", **extra):
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
        return Archive.objects.create(**values)

    def private_files(self):
        return [path for path in Path(self.private_media.name).rglob("*") if path.is_file()]


class SecurityHeadersAndHealthTests(PlatformTestCase):
    def test_strict_content_security_policy_is_sent_without_unsafe_inline(self):
        response = self.client.get(reverse("login"))

        policy = response["Content-Security-Policy"]
        self.assertIn("default-src 'self'", policy)
        self.assertIn("script-src 'self'", policy)
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertNotIn("unsafe-inline", policy)
        self.assertIn("camera=()", response["Permissions-Policy"])

    def test_admin_keeps_scripts_strict_but_allows_its_inline_styles(self):
        response = self.client.get("/admin/login/")

        policy = response["Content-Security-Policy"]
        self.assertIn("style-src 'self' 'unsafe-inline'", policy)
        self.assertIn("script-src 'self'", policy)
        self.assertNotIn("script-src 'self' 'unsafe-inline'", policy)

    def test_templates_contain_no_inline_script_or_style_attribute(self):
        templates_root = Path(__file__).resolve().parents[1] / "templates"
        for template in templates_root.rglob("*.html"):
            source = template.read_text(encoding="utf-8")
            with self.subTest(template=template.name):
                self.assertNotIn(' style="', source)
                for line in source.splitlines():
                    if "<script" in line:
                        self.assertTrue(
                            "src=" in line or "json_script" in line,
                            f"Script en ligne interdit par la CSP : {line.strip()}",
                        )

    def test_health_endpoint_checks_database_without_details(self):
        response = self.client.get(reverse("healthz"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertIn("no-cache", response["Cache-Control"])

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_health_endpoint_is_exempt_from_https_redirect(self):
        client = Client()

        self.assertEqual(client.get("/healthz/").status_code, 200)
        self.assertEqual(client.get("/accounts/login/").status_code, 301)

    def test_health_endpoint_reports_database_failure_as_503(self):
        from django.db.utils import OperationalError

        with patch("config.views.connection.cursor", side_effect=OperationalError("down")):
            response = self.client.get(reverse("healthz"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})

    def test_session_lifetime_is_a_working_day(self):
        from django.conf import settings

        self.assertEqual(settings.SESSION_COOKIE_AGE, 8 * 60 * 60)


@override_settings(AUTH_LOGIN_FAILURE_LIMIT=3, AUTH_LOGIN_LOCKOUT_SECONDS=600)
class LoginThrottleTests(PlatformTestCase):
    def attempt(self, email, password):
        return self.client.post(reverse("login"), {"username": email, "password": password})

    def test_repeated_failures_lock_the_account_temporarily(self):
        for _ in range(2):
            self.assertEqual(self.attempt(self.agent.email, "wrong-password").status_code, 200)

        locked = self.attempt(self.agent.email, "wrong-password")

        self.assertEqual(locked.status_code, 429)
        self.assertContains(locked, "Trop de tentatives", status_code=429)

    def test_correct_password_is_refused_while_locked(self):
        for _ in range(3):
            self.attempt(self.agent.email, "wrong-password")

        response = self.attempt(self.agent.email, PASSWORD)

        self.assertEqual(response.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_lockout_is_scoped_to_the_targeted_identifier_and_case_insensitive(self):
        for _ in range(3):
            self.attempt(self.agent.email.upper(), "wrong-password")

        self.assertEqual(self.attempt(self.agent.email, PASSWORD).status_code, 429)
        response = self.attempt(self.consultant.email, PASSWORD)
        self.assertRedirects(response, "/")

    def test_successful_login_resets_the_failure_counter(self):
        for _ in range(2):
            self.attempt(self.agent.email, "wrong-password")
        self.assertRedirects(self.attempt(self.agent.email, PASSWORD), "/")
        self.client.logout()

        for _ in range(2):
            self.assertEqual(self.attempt(self.agent.email, "wrong-password").status_code, 200)

    def test_cache_keys_do_not_store_identifiers_in_clear(self):
        from accounts.throttling import _key

        key = _key("login", self.agent.email)

        self.assertNotIn(self.agent.email, key)
        self.assertTrue(key.startswith("ctech:throttle:login:"))


@override_settings(AUTH_SIGNUP_LIMIT=2)
class SignupThrottleTests(PlatformTestCase):
    def signup(self, index):
        return self.client.post(
            reverse("signup"),
            {
                "email": f"burst-{index}@example.test",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )

    def test_signup_burst_from_the_same_origin_is_limited(self):
        for index in range(2):
            self.assertRedirects(self.signup(index), "/")
            self.client.logout()

        response = self.signup(99)

        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Trop d’inscriptions récentes", status_code=429)
        self.assertFalse(get_user_model().objects.filter(email="burst-99@example.test").exists())


class AccountSelfServiceTests(PlatformTestCase):
    def test_password_change_requires_authentication(self):
        url = reverse("password_change")

        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_password_change_updates_password_keeps_session_and_is_audited(self):
        self.client.force_login(self.agent)
        new_password = "Brand-New-Synthetic-Password-2026!"

        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": PASSWORD,
                "new_password1": new_password,
                "new_password2": new_password,
            },
        )

        self.assertRedirects(response, reverse("profile"))
        self.agent.refresh_from_db()
        self.assertTrue(self.agent.check_password(new_password))
        self.assertEqual(self.client.get(reverse("profile")).status_code, 200)
        self.assertTrue(
            AuditLog.objects.filter(actor=self.agent, action=AuditAction.PASSWORD_CHANGE).exists()
        )

    def test_password_change_rejects_wrong_current_password_without_audit(self):
        self.client.force_login(self.agent)

        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": "not-the-password",
                "new_password1": "Brand-New-Synthetic-Password-2026!",
                "new_password2": "Brand-New-Synthetic-Password-2026!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(AuditLog.objects.filter(action=AuditAction.PASSWORD_CHANGE).exists())

    def test_avatar_can_be_removed_by_its_owner(self):
        self.consultant.profile_avatar = png_bytes()
        self.consultant.profile_avatar_content_type = "image/png"
        self.consultant.save(update_fields=["profile_avatar", "profile_avatar_content_type"])
        self.client.force_login(self.consultant)

        response = self.client.post(reverse("profile"), {"action": "remove-avatar"})

        self.assertRedirects(response, reverse("profile"))
        self.consultant.refresh_from_db()
        self.assertFalse(self.consultant.has_profile_avatar)
        self.assertEqual(
            self.client.get(reverse("profile_avatar", args=[self.consultant.pk])).status_code,
            404,
        )

    def test_session_user_is_loaded_without_avatar_bytes(self):
        self.consultant.profile_avatar = png_bytes()
        self.consultant.profile_avatar_content_type = "image/png"
        self.consultant.save(update_fields=["profile_avatar", "profile_avatar_content_type"])
        from accounts.backends import EmailBackend

        user = EmailBackend().get_user(self.consultant.pk)

        self.assertIn("profile_avatar", user.get_deferred_fields())
        self.assertTrue(user.has_profile_avatar)

    def test_profile_shows_clearance_for_the_current_role(self):
        self.client.force_login(self.consultant)

        response = self.client.get(reverse("profile"))

        self.assertContains(response, "Mon habilitation")
        self.assertContains(response, "Non accessible")
        self.assertEqual(response.context["clearance_granted_count"], 1)


class CommandPaletteTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.public = self.create_archive("CT-PAL-PUB", ConfidentialityLevel.PUBLIC)
        self.internal = self.create_archive("CT-PAL-INT", ConfidentialityLevel.INTERNAL)
        self.confidential = self.create_archive("CT-PAL-CONF", ConfidentialityLevel.CONFIDENTIAL)
        self.url = reverse("archives:quick_search")

    def references(self, user, query="CT-PAL"):
        self.client.force_login(user)
        response = self.client.get(self.url, {"q": query})
        self.assertEqual(response.status_code, 200)
        return {result["reference"] for result in response.json()["results"]}

    def test_quick_search_is_filtered_by_rbac(self):
        self.assertEqual(self.references(self.consultant), {"CT-PAL-PUB"})
        self.assertEqual(self.references(self.agent), {"CT-PAL-PUB", "CT-PAL-INT"})
        self.assertEqual(
            self.references(self.admin), {"CT-PAL-PUB", "CT-PAL-INT", "CT-PAL-CONF"}
        )

    def test_quick_search_requires_authentication_and_a_meaningful_query(self):
        response = self.client.get(self.url, {"q": "CT"})
        self.assertEqual(response.status_code, 302)

        self.assertEqual(self.references(self.admin, "C"), set())

    def test_quick_search_exposes_no_checksum_and_records_no_consultation(self):
        archive = self.create_archive("CT-PAL-FILE", content=b"%PDF-1.4 palette")
        self.client.force_login(self.admin)

        response = self.client.get(self.url, {"q": "CT-PAL-FILE"})

        self.assertNotContains(response, archive.checksum)
        self.assertNotContains(response, archive.file.name)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertFalse(AuditLog.objects.exclude(action=AuditAction.LOGIN).exists())

    def test_palette_commands_are_filtered_by_role(self):
        self.client.force_login(self.consultant)
        consultant_labels = {item["label"] for item in self.client.get("/").context["command_items"]}
        self.client.force_login(self.admin)
        admin_labels = {item["label"] for item in self.client.get("/").context["command_items"]}

        self.assertNotIn("Nouvelle archive", consultant_labels)
        self.assertNotIn("Journal d’audit", consultant_labels)
        self.assertIn("Nouvelle archive", admin_labels)
        self.assertIn("Journal d’audit", admin_labels)


class ArchivePreviewTests(PlatformTestCase):
    def preview(self, user, archive):
        self.client.force_login(user)
        return self.client.get(reverse("archives:preview", args=[archive.pk]))

    def test_image_preview_is_isolated_and_audited(self):
        archive = self.create_archive("CT-PRE-PNG", content=png_bytes(), extension="png")

        response = self.preview(self.consultant, archive)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["Content-Disposition"], "inline")
        self.assertIn("sandbox", response["Content-Security-Policy"])
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertTrue(
            AuditLog.objects.filter(archive=archive, action=AuditAction.ARCHIVE_PREVIEW).exists()
        )

    def test_text_preview_is_truncated_and_served_as_plain_text(self):
        archive = self.create_archive("CT-PRE-TXT", content=b"a" * (70 * 1024), extension="txt")

        response = self.preview(self.agent, archive)

        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        self.assertEqual(response["X-Preview-Truncated"], "true")
        self.assertEqual(len(response.content), 64 * 1024)

    def test_hidden_archive_preview_is_not_found_for_lower_roles(self):
        archive = self.create_archive(
            "CT-PRE-CONF", ConfidentialityLevel.CONFIDENTIAL, content=png_bytes(), extension="png"
        )

        self.assertEqual(self.preview(self.consultant, archive).status_code, 404)
        self.assertEqual(self.preview(self.agent, archive).status_code, 404)
        self.assertFalse(AuditLog.objects.filter(action=AuditAction.ARCHIVE_PREVIEW).exists())

    def test_pdf_and_forged_images_are_never_rendered_inline(self):
        pdf = self.create_archive("CT-PRE-PDF", content=b"%PDF-1.4 preview")
        forged = self.create_archive("CT-PRE-FAKE", content=b"<svg onload=alert(1)>", extension="png")

        self.assertEqual(self.preview(self.admin, pdf).status_code, 404)
        self.assertEqual(self.preview(self.admin, forged).status_code, 404)

    def test_detail_offers_preview_only_for_supported_kinds(self):
        image = self.create_archive("CT-PRE-IMG", content=png_bytes(), extension="png")
        pdf = self.create_archive("CT-PRE-DOC", content=b"%PDF-1.4 preview")
        self.client.force_login(self.admin)

        self.assertContains(self.client.get(reverse("archives:detail", args=[image.pk])), "data-preview-url")
        self.assertNotContains(self.client.get(reverse("archives:detail", args=[pdf.pk])), "data-preview-url")


class ArchiveDetailV2Tests(PlatformTestCase):
    def test_integrity_state_reflects_the_last_verification(self):
        archive = self.create_archive("CT-INT-OK", content=b"%PDF-1.4 integrity")
        self.client.force_login(self.agent)

        before = self.client.get(reverse("archives:detail", args=[archive.pk]))
        self.client.post(reverse("archives:verify_integrity", args=[archive.pk]))
        after = self.client.get(reverse("archives:detail", args=[archive.pk]))

        self.assertEqual(before.context["integrity_state"]["tone"], "unknown")
        self.assertEqual(after.context["integrity_state"]["tone"], "valid")
        self.assertContains(after, "Fichier conforme")

    def test_tampered_file_raises_an_integrity_alert_on_the_detail(self):
        archive = self.create_archive("CT-INT-KO", content=b"%PDF-1.4 integrity")
        with archive.file.storage.open(archive.file.name, "ab") as handle:
            handle.write(b"tampered")
        self.client.force_login(self.admin)

        self.client.post(reverse("archives:verify_integrity", args=[archive.pk]))
        response = self.client.get(reverse("archives:detail", args=[archive.pk]))

        self.assertEqual(response.context["integrity_state"]["tone"], "alert")
        self.assertContains(response, "Alerte d’intégrité")

    def test_access_history_is_reserved_to_audit_viewers(self):
        archive = self.create_archive("CT-HIST", content=b"%PDF-1.4 history")
        self.client.force_login(self.admin)
        admin_response = self.client.get(reverse("archives:detail", args=[archive.pk]))
        self.client.force_login(self.agent)
        agent_response = self.client.get(reverse("archives:detail", args=[archive.pk]))

        self.assertContains(admin_response, "Historique des accès")
        self.assertNotIn("archive_history", agent_response.context)
        self.assertNotContains(agent_response, "Historique des accès")
        self.assertContains(agent_response, "Cycle de vie")

    def test_detail_never_exposes_the_stored_file_name_or_checksum(self):
        archive = self.create_archive("CT-HIDE", content=b"%PDF-1.4 hidden")
        self.client.force_login(self.admin)

        response = self.client.get(reverse("archives:detail", args=[archive.pk]))

        self.assertNotContains(response, archive.file.name)
        self.assertNotContains(response, archive.checksum)
        self.assertContains(response, "CT-HIDE.pdf")


class ArchiveListV2Tests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.zeta = self.create_archive("CT-Z", title="Zeta")
        self.alpha = self.create_archive("CT-A", title="Alpha")

    def test_sorting_uses_a_whitelist(self):
        self.client.force_login(self.admin)

        by_title = self.client.get(reverse("archives:list"), {"sort": "title"})
        forged = self.client.get(reverse("archives:list"), {"sort": "checksum"})

        self.assertEqual([a.reference for a in by_title.context["archives"]], ["CT-A", "CT-Z"])
        self.assertEqual(forged.context["sort"], "recent")

    def test_grid_view_and_presentation_parameters_are_not_a_search(self):
        Archive.objects.all().delete()
        self.client.force_login(self.admin)

        response = self.client.get(reverse("archives:list"), {"view": "grid", "sort": "title"})

        self.assertFalse(response.context["has_active_search"])
        self.assertContains(response, "Aucune archive disponible")

    def test_grid_view_renders_cards_with_post_integrity_forms(self):
        archive = self.create_archive("CT-GRID", content=b"%PDF-1.4 grid")
        self.client.force_login(self.consultant)

        response = self.client.get(reverse("archives:list"), {"view": "grid"})

        self.assertContains(response, "archive-card")
        self.assertContains(response, f'action="/archives/{archive.pk}/verify-integrity/"')

    def test_active_filters_are_listed_with_removal_links(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("archives:list"), {"q": "Alpha", "status": "ACTIVE"})

        labels = {chip["label"] for chip in response.context["active_filters"]}
        self.assertEqual(labels, {"Recherche", "Statut"})
        self.assertContains(response, "Retirer le filtre")


class AuditExportTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.admin.username = "=HYPERLINK(\"http://evil.test\")"
        self.admin.save(update_fields=["username"])
        AuditLog.objects.create(
            actor=self.admin,
            actor_identifier=self.admin.username,
            action=AuditAction.LOGIN,
            ip_address="127.0.0.1",
        )

    def test_export_is_reserved_to_administrators(self):
        for user in (self.agent, self.consultant):
            with self.subTest(user=user.email):
                self.client.force_login(user)
                self.assertEqual(self.client.get(reverse("audit:export")).status_code, 403)

    def test_export_neutralizes_spreadsheet_formulas_and_is_audited(self):
        self.client.force_login(self.admin)
        login_events = AuditLog.objects.filter(action=AuditAction.LOGIN).count()

        response = self.client.get(reverse("audit:export"), {"action": AuditAction.LOGIN})
        content = b"".join(response.streaming_content).decode("utf-8-sig")
        rows = list(csv.reader(StringIO(content), delimiter=";"))

        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertEqual(rows[0], ["horodatage", "utilisateur", "action", "archive", "adresse_ip"])
        self.assertTrue(any(row[1].startswith("'=HYPERLINK") for row in rows[1:]))
        self.assertFalse(any(row[1].startswith("=") for row in rows[1:]))
        export_event = AuditLog.objects.get(action=AuditAction.AUDIT_EXPORT)
        self.assertEqual(export_event.details, {"source": "web", "row_count": login_events})

    def test_audit_list_supports_date_range_and_groups_by_day(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("audit:list"), {"from": "2000-01-01", "to": "2000-01-02"})
        today = self.client.get(reverse("audit:list"))

        self.assertEqual(response.context["result_count"], 0)
        self.assertContains(response, "Aucun événement trouvé")
        self.assertContains(today, "Aujourd’hui")
        self.assertEqual(len(today.context["event_groups"]), 1)

    def test_invalid_dates_are_ignored_instead_of_failing(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("audit:list"), {"from": "not-a-date"})

        self.assertEqual(response.status_code, 200)


class DashboardAnalyticsTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.create_archive("CT-DASH-PUB", ConfidentialityLevel.PUBLIC, content=b"%PDF-1.4 a")
        self.create_archive("CT-DASH-INT", ConfidentialityLevel.INTERNAL)
        self.create_archive("CT-DASH-CONF", ConfidentialityLevel.CONFIDENTIAL)

    def test_consultant_analytics_never_reflect_hidden_levels(self):
        self.client.force_login(self.consultant)

        context = self.client.get("/").context

        self.assertEqual([segment["value"] for segment in context["donut"]["segments"]], ["public"])
        self.assertEqual(context["donut"]["total"], 1)
        self.assertEqual(context["monthly"]["total"], 1)
        self.assertEqual(context["integrity"]["total"], 1)
        self.assertEqual(sum(row["total"] for row in context["services_ranking"]), 1)
        self.assertNotIn("heatmap", context)
        self.assertNotIn("action_ranking", context)

    def test_administrator_sees_all_levels_and_the_audit_pulse(self):
        self.client.force_login(self.admin)

        response = self.client.get("/")

        self.assertEqual(len(response.context["donut"]["segments"]), 3)
        self.assertEqual(response.context["integrity"]["sealed"], 1)
        self.assertContains(response, "Pouls du journal")
        self.assertContains(response, "Actions les plus fréquentes")

    def test_svg_geometry_is_never_localized(self):
        self.assertEqual(svg_number(187.5), "187.5")
        self.assertEqual(svg_number(0), "0")
        self.client.force_login(self.admin)

        response = self.client.get("/")

        for point in response.context["monthly"]["points"]:
            self.assertNotIn(",", point["x"] + point["y"] + point["height"])


class SealTests(TestCase):
    def test_seal_is_deterministic_and_unique_per_reference(self):
        self.assertEqual(seal_geometry("CT-0001"), seal_geometry("CT-0001"))
        self.assertNotEqual(seal_geometry("CT-0001")["segments"], seal_geometry("CT-0002")["segments"])

    def test_seal_label_is_escaped(self):
        markup = render_seal("CT-0001", label='<script>alert("x")</script>')

        self.assertNotIn("<script>", markup)
        self.assertIn('role="img"', markup)

    def test_decorative_seal_is_hidden_from_assistive_technologies(self):
        self.assertIn('aria-hidden="true"', render_seal("CT-0001"))


class OrphanFileCleanupTests(PlatformTestCase):
    def test_file_is_removed_when_the_creation_transaction_fails(self):
        self.client.raise_request_exception = True
        self.client.force_login(self.admin)

        with patch("archives.views.record_audit_event", side_effect=RuntimeError("audit down")):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    reverse("archives:create"),
                    {
                        "reference": "CT-ORPHAN",
                        "title": "Orpheline",
                        "category": self.category.pk,
                        "document_type": self.document_type.pk,
                        "service": self.service.pk,
                        "status": ArchiveStatus.ACTIVE,
                        "confidentiality_level": ConfidentialityLevel.PUBLIC,
                        "file": SimpleUploadedFile(
                            "orphan.pdf", b"%PDF-1.4 orphan", content_type="application/pdf"
                        ),
                    },
                )

        self.assertFalse(Archive.objects.filter(reference="CT-ORPHAN").exists())
        self.assertEqual(self.private_files(), [])


class BootstrapCreateOnlyTests(TestCase):
    environment = {
        "CTECH_STEVEN_EMAIL": "steven.v2@example.test",
        "CTECH_STEVEN_PASSWORD": "Steven-Synthetic-Password-2026",
        "CTECH_EULOGE_EMAIL": "euloge.v2@example.test",
        "CTECH_EULOGE_PASSWORD": "Euloge-Synthetic-Password-2026",
    }

    def run_command(self, *args, environment=None):
        stdout, stderr = StringIO(), StringIO()
        with patch.dict(os.environ, environment or self.environment, clear=True):
            call_command("bootstrap_default_admins", *args, stdout=stdout, stderr=stderr)
        return stdout.getvalue(), stderr.getvalue()

    def test_create_only_never_reactivates_or_resets_an_existing_admin(self):
        self.run_command()
        steven = get_user_model().objects.get(email="steven.v2@example.test")
        steven.is_active = False
        steven.set_password("Changed-By-Steven-2026!")
        steven.save()

        stdout, _ = self.run_command("--create-only")

        steven.refresh_from_db()
        self.assertFalse(steven.is_active)
        self.assertTrue(steven.check_password("Changed-By-Steven-2026!"))
        self.assertIn("create-only", stdout)
        self.assertIn("2 left unchanged", stdout)

    def test_explicit_reconcile_flag_restores_reconciliation(self):
        self.run_command()
        steven = get_user_model().objects.get(email="steven.v2@example.test")
        steven.is_active = False
        steven.save(update_fields=["is_active"])

        self.run_command(
            "--create-only",
            environment={**self.environment, "CTECH_BOOTSTRAP_RECONCILE": "true"},
        )

        steven.refresh_from_db()
        self.assertTrue(steven.is_active)

    def test_weak_password_is_rejected_without_creating_accounts(self):
        weak = {**self.environment, "CTECH_STEVEN_PASSWORD": "123"}

        with self.assertRaisesMessage(CommandError, "CTECH_STEVEN_PASSWORD") as context:
            self.run_command(environment=weak)

        self.assertNotIn("123", str(context.exception).replace("CTECH", ""))
        self.assertFalse(get_user_model().objects.exists())

    def test_allow_missing_skips_startup_bootstrap_without_failing(self):
        stdout, stderr = self.run_command("--create-only", "--allow-missing", environment={"PATH": ""})

        self.assertIn("skipped", stderr)
        self.assertEqual(stdout, "")
        self.assertFalse(get_user_model().objects.exists())


class SeedDemoTests(TestCase):
    def setUp(self):
        self.private_media = TemporaryDirectory()
        self.override = override_settings(PRIVATE_MEDIA_ROOT=self.private_media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.private_media.cleanup)

    def test_seed_is_refused_in_production(self):
        with override_settings(DJANGO_ENV="production"):
            with self.assertRaisesMessage(CommandError, "production"):
                call_command("seed_demo", password=PASSWORD, stdout=StringIO())

    def test_seed_requires_a_strong_password(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CTECH_DEMO_PASSWORD", None)
            with self.assertRaises(CommandError):
                call_command("seed_demo", stdout=StringIO())
        with self.assertRaisesMessage(CommandError, "trop faible"):
            call_command("seed_demo", password="123", stdout=StringIO())

    def test_seed_is_idempotent_rbac_consistent_and_never_prints_the_password(self):
        output = StringIO()
        call_command("seed_demo", password=PASSWORD, archives=8, stdout=output)
        call_command("seed_demo", password=PASSWORD, archives=8, stdout=StringIO())

        self.assertEqual(Archive.objects.filter(reference__startswith="CT-DEMO-").count(), 8)
        self.assertEqual(get_user_model().objects.filter(email__endswith="@ctech.test").count(), 3)
        self.assertNotIn(PASSWORD, output.getvalue())
        consultant = get_user_model().objects.get(email="demo.consultant@ctech.test")
        self.assertFalse(
            AuditLog.objects.filter(actor=consultant, action=AuditAction.ARCHIVE_UPDATE).exists()
        )
        self.assertFalse(
            AuditLog.objects.filter(actor=consultant)
            .exclude(archive=None)
            .exclude(archive__confidentiality_level=ConfidentialityLevel.PUBLIC)
            .exists()
        )
        for archive in Archive.objects.exclude(file="").exclude(reference="CT-DEMO-0013"):
            with archive.file.open("rb") as handle:
                self.assertEqual(sha256(handle.read()).hexdigest(), archive.checksum)
