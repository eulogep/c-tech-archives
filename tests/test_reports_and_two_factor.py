"""Tests des rapports, exports et de la sécurité renforcée (double authentification)."""

import csv
import time
from io import StringIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts import totp
from accounts.models import RecoveryCode, Role
from archives.models import (
    Archive,
    ArchiveStatus,
    Category,
    ConfidentialityLevel,
    DocumentType,
    Service,
)
from audit.models import AuditAction, AuditLog


PASSWORD = "Synthetic-Security-Password-2026!"


class SecurityTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.private_media = TemporaryDirectory()
        self.override = override_settings(PRIVATE_MEDIA_ROOT=self.private_media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.private_media.cleanup)
        users = get_user_model().objects
        self.admin = users.create_user(
            username="sec-admin@example.test", email="sec-admin@example.test",
            password=PASSWORD, role=Role.ADMINISTRATEUR, first_name="Ada", last_name="Admin",
        )
        self.agent = users.create_user(
            username="sec-agent@example.test", email="sec-agent@example.test",
            password=PASSWORD, role=Role.AGENT_ARCHIVES,
        )
        self.consultant = users.create_user(
            username="sec-consultant@example.test", email="sec-consultant@example.test",
            password=PASSWORD, role=Role.CONSULTANT,
        )
        service = Service.objects.create(name="=Service formule")
        category = Category.objects.create(name="Catégorie sécurité")
        document_type = DocumentType.objects.create(name="Type sécurité")
        for reference, level in (
            ("CT-SEC-PUB", ConfidentialityLevel.PUBLIC),
            ("CT-SEC-INT", ConfidentialityLevel.INTERNAL),
            ("CT-SEC-CONF", ConfidentialityLevel.CONFIDENTIAL),
        ):
            Archive.objects.create(
                reference=reference, title=f"Titre {reference}", category=category,
                document_type=document_type, service=service, uploaded_by=self.admin,
                status=ArchiveStatus.ACTIVE, confidentiality_level=level, checksum="a" * 64,
            )


class ArchiveExportTests(SecurityTestCase):
    def export(self, user, **params):
        self.client.force_login(user)
        response = self.client.get(reverse("archives:export"), params)
        content = b"".join(response.streaming_content).decode("utf-8-sig")
        return response, list(csv.reader(StringIO(content), delimiter=";"))

    def test_export_follows_rbac_filters_and_is_audited(self):
        _, consultant_rows = self.export(self.consultant)
        _, admin_rows = self.export(self.admin, q="CT-SEC-CONF")

        self.assertEqual([row[0] for row in consultant_rows[1:]], ["CT-SEC-PUB"])
        self.assertEqual([row[0] for row in admin_rows[1:]], ["CT-SEC-CONF"])
        event = AuditLog.objects.filter(action=AuditAction.ARCHIVE_EXPORT, actor=self.consultant).get()
        self.assertEqual(event.details["row_count"], 1)

    def test_export_never_contains_checksums_and_neutralizes_formulas(self):
        response, rows = self.export(self.admin)

        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertNotIn("a" * 64, str(rows))
        self.assertTrue(all(row[2] == "'=Service formule" for row in rows[1:]))
        self.assertEqual({row[11] for row in rows[1:]}, {"oui"})


class ActivityReportTests(SecurityTestCase):
    def test_report_is_limited_to_the_visible_scope(self):
        self.client.force_login(self.consultant)

        response = self.client.get(reverse("report"), {"days": 90})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["report"]["total"], 1)
        self.assertEqual(response.context["report"]["days"], 90)
        self.assertNotIn("audit", response.context["report"])
        self.assertNotContains(response, "Activité du journal d’audit")

    def test_administrator_report_includes_audit_activity_and_bad_periods_fall_back(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("report"), {"days": "abc"})
        weird = self.client.get(reverse("report"), {"days": 7})

        self.assertEqual(response.context["report"]["total"], 3)
        self.assertIn("audit", response.context["report"])
        self.assertContains(response, "Activité du journal d’audit")
        self.assertEqual(weird.context["report"]["days"], 30)


class TotpTests(TestCase):
    def test_rfc_6238_reference_vector(self):
        secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # « 12345678901234567890 »

        self.assertEqual(totp.code_at(secret, 1), "287082")
        self.assertEqual(totp.verify(secret, "287 082", now=59), 1)

    def test_window_and_replay_protection(self):
        secret = totp.generate_secret()
        now = time.time()
        counter = totp.current_counter(now)
        previous = totp.code_at(secret, counter - 1)

        self.assertEqual(totp.verify(secret, previous, now=now), counter - 1)
        self.assertIsNone(totp.verify(secret, previous, last_counter=counter - 1, now=now))
        self.assertIsNone(totp.verify(secret, totp.code_at(secret, counter - 5), now=now))
        self.assertIsNone(totp.verify(secret, "12345", now=now))

    def test_recovery_codes_are_random_and_only_hashes_are_comparable(self):
        codes = totp.generate_recovery_codes()

        self.assertEqual(len(set(codes)), 8)
        self.assertEqual(totp.hash_recovery_code(codes[0].upper()), totp.hash_recovery_code(codes[0]))
        self.assertNotIn(codes[0], totp.hash_recovery_code(codes[0]))


class TwoFactorFlowTests(SecurityTestCase):
    def enable_for(self, user):
        self.client.force_login(user)
        self.client.get(reverse("two_factor"))
        secret = self.client.session["ctech_2fa_setup_secret"]
        response = self.client.post(
            reverse("two_factor"),
            {"action": "enable", "code": totp.code_at(secret, totp.current_counter())},
        )
        # Ne pas suivre la redirection : les codes de secours ne s’affichent qu’une fois.
        self.assertRedirects(response, reverse("two_factor"), fetch_redirect_response=False)
        page = self.client.get(reverse("two_factor"))
        self.client.logout()
        user.refresh_from_db()
        return secret, page.context["new_codes"]

    def test_setup_page_offers_a_qr_code_without_enabling_anything(self):
        self.client.force_login(self.agent)

        response = self.client.get(reverse("two_factor"))

        self.assertContains(response, "data:image/svg+xml")
        self.agent.refresh_from_db()
        self.assertFalse(self.agent.totp_enabled)

    def test_enable_shows_recovery_codes_once_and_is_audited(self):
        secret, codes = self.enable_for(self.agent)

        self.assertTrue(self.agent.totp_enabled)
        self.assertEqual(self.agent.totp_secret, secret)
        self.assertEqual(len(codes), 8)
        self.assertEqual(RecoveryCode.objects.filter(user=self.agent).count(), 8)
        self.assertFalse(RecoveryCode.objects.filter(code_hash__in=codes).exists())
        self.assertTrue(AuditLog.objects.filter(actor=self.agent, action=AuditAction.TWO_FACTOR_ENABLE).exists())
        self.client.force_login(self.agent)
        self.assertIsNone(self.client.get(reverse("two_factor")).context["new_codes"])

    def test_wrong_confirmation_code_does_not_enable(self):
        self.client.force_login(self.agent)
        self.client.get(reverse("two_factor"))

        self.client.post(reverse("two_factor"), {"action": "enable", "code": "000000"})

        self.agent.refresh_from_db()
        self.assertFalse(self.agent.totp_enabled)

    def test_password_alone_no_longer_opens_a_session(self):
        secret, _ = self.enable_for(self.agent)

        response = self.client.post(
            f"{reverse('login')}?next=/archives/",
            {"username": self.agent.email, "password": PASSWORD},
        )

        self.assertRedirects(response, reverse("login_verify"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.get("/").status_code, 302)

        wrong = self.client.post(reverse("login_verify"), {"code": "000000"})
        self.assertContains(wrong, "Code invalide")
        self.assertTrue(AuditLog.objects.filter(actor=self.agent, action=AuditAction.TWO_FACTOR_FAILURE).exists())

        # Le code de la période suivante : celui de l’activation est refusé (anti-rejeu).
        code = totp.code_at(secret, totp.current_counter() + 1)
        right = self.client.post(reverse("login_verify"), {"code": code})
        self.assertRedirects(right, "/archives/", fetch_redirect_response=False)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.agent.pk))

    def test_recovery_code_works_exactly_once(self):
        _, codes = self.enable_for(self.agent)

        for attempt in range(2):
            self.client.post(reverse("login"), {"username": self.agent.email, "password": PASSWORD})
            response = self.client.post(reverse("login_verify"), {"code": codes[0]})
            if attempt == 0:
                self.assertRedirects(response, "/", fetch_redirect_response=False)
                self.client.logout()
            else:
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(AuditLog.objects.filter(actor=self.agent, action=AuditAction.RECOVERY_CODE_USED).exists())

    def test_pending_verification_expires(self):
        self.enable_for(self.agent)
        self.client.post(reverse("login"), {"username": self.agent.email, "password": PASSWORD})
        session = self.client.session
        session["ctech_2fa_pending"]["issued"] = time.time() - 600
        session.save()

        response = self.client.get(reverse("login_verify"))

        self.assertRedirects(response, reverse("login"))

    @override_settings(AUTH_LOGIN_FAILURE_LIMIT=2)
    def test_code_guessing_is_throttled(self):
        self.enable_for(self.agent)
        self.client.post(reverse("login"), {"username": self.agent.email, "password": PASSWORD})

        self.client.post(reverse("login_verify"), {"code": "000000"})
        locked = self.client.post(reverse("login_verify"), {"code": "000001"})

        self.assertEqual(locked.status_code, 429)

    def test_disable_requires_password_and_code(self):
        secret, codes = self.enable_for(self.agent)
        self.client.force_login(self.agent)

        self.client.post(reverse("two_factor"), {"action": "disable", "password": "wrong", "code": codes[1]})
        self.agent.refresh_from_db()
        self.assertTrue(self.agent.totp_enabled)

        self.client.post(reverse("two_factor"), {"action": "disable", "password": PASSWORD, "code": codes[1]})
        self.agent.refresh_from_db()
        self.assertFalse(self.agent.totp_enabled)
        self.assertEqual(self.agent.totp_secret, "")
        self.assertFalse(RecoveryCode.objects.filter(user=self.agent).exists())


class AccessReviewTests(SecurityTestCase):
    def test_review_is_reserved_to_administrators(self):
        for user in (self.agent, self.consultant):
            with self.subTest(user=user.email):
                self.client.force_login(user)
                self.assertEqual(self.client.get(reverse("access_review")).status_code, 403)

    def test_review_highlights_privileged_accounts_without_second_factor(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("access_review"), {"focus": "privileged"})

        self.assertEqual(response.context["summary"]["privileged_without_2fa"], 1)
        self.assertEqual({account.email for account in response.context["accounts"]}, {self.admin.email})
        self.assertContains(response, "Absente")
