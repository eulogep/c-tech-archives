"""Jeu de démonstration réaliste pour une soutenance ou un poste de développement.

La commande refuse de s’exécuter en production, n’affiche aucun mot de passe et
est idempotente : une seconde exécution ne crée aucun doublon. Le mot de passe
des comptes de démonstration est fourni par ``--password`` ou par la variable
``CTECH_DEMO_PASSWORD`` et doit respecter AUTH_PASSWORD_VALIDATORS.
"""

from __future__ import annotations

import os
import random
from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw

from accounts.models import Role
from archives.integrity import calculate_archive_checksum
from archives.permissions import can_create_archive, visible_confidentiality_levels_for
from archives.search import update_search_document
from archives.text_extraction import extract_text
from archives.models import (
    Archive,
    ArchiveStatus,
    Category,
    ConfidentialityLevel,
    DocumentType,
    Service,
)
from audit.models import AuditAction, AuditLog


DEMO_USERS = (
    ("demo.admin@ctech.test", "Awa", "Diallo", Role.ADMINISTRATEUR),
    ("demo.agent@ctech.test", "Lucas", "Martin", Role.AGENT_ARCHIVES),
    ("demo.consultant@ctech.test", "Inès", "Moreau", Role.CONSULTANT),
)
SERVICES = (
    "Direction générale",
    "Ressources humaines",
    "Finances & comptabilité",
    "Affaires juridiques",
    "Systèmes d’information",
    "Achats & logistique",
)
CATEGORIES = (
    "Contrats",
    "Rapports",
    "Procès-verbaux",
    "Correspondance",
    "Pièces comptables",
    "Politiques internes",
)
DOCUMENT_TYPES = (
    "Contrat de prestation",
    "Rapport d’activité",
    "Compte rendu de réunion",
    "Note de service",
    "Facture fournisseur",
    "Charte interne",
)
TITLES = (
    "Contrat cadre de maintenance du parc informatique",
    "Rapport annuel d’activité {year}",
    "Procès-verbal du comité de direction",
    "Note de service relative au télétravail",
    "Facture de renouvellement des licences",
    "Charte d’usage des outils numériques",
    "Avenant au contrat de nettoyage des locaux",
    "Compte rendu de l’audit de sécurité",
    "Plan de continuité d’activité",
    "Registre des traitements de données",
    "Convention de stage — promotion {year}",
    "Budget prévisionnel {year}",
    "Politique de conservation des archives",
    "Rapport d’incident réseau",
    "Accord de confidentialité partenaire",
    "Procédure d’accueil des nouveaux arrivants",
    "Bilan social {year}",
    "Bon de commande mobilier de bureau",
)
LEVEL_WEIGHTS = (
    (ConfidentialityLevel.PUBLIC, 4),
    (ConfidentialityLevel.INTERNAL, 4),
    (ConfidentialityLevel.CONFIDENTIAL, 2),
)
TAMPERED_REFERENCE = "CT-DEMO-0013"


BODY_LINES = (
    "Objet : pièce de démonstration pour la recherche plein texte.",
    "Le prestataire s’engage à respecter la confidentialité des données.",
    "Échéance de révision : à planifier avec le service concerné.",
    "Sécurité : accès restreint selon l’habilitation du lecteur.",
    "Budget, facturation et pénalités de retard détaillés en annexe.",
)


def _pdf_bytes(title: str, rng=None) -> bytes:
    """PDF minimal mais valide, sans dépendance supplémentaire (police standard, WinAnsi)."""
    def escape(text):
        return text.encode("cp1252", "replace").replace(b"(", b"[").replace(b")", b"]")

    lines = list(BODY_LINES)
    if rng is not None:
        rng.shuffle(lines)
    stream = b"BT /F1 18 Tf 72 760 Td (" + escape(title) + b") Tj ET"
    for index, line in enumerate(lines[:4]):
        stream += b"\nBT /F1 11 Tf 72 " + str(720 - index * 18).encode() + b" Td (" + escape(line) + b") Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    output = BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        output.write(f"{offset:010d} 00000 n \n".encode())
    output.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return output.getvalue()


def _png_bytes(seed: int) -> bytes:
    rng = random.Random(seed)
    image = Image.new("RGB", (640, 400), (18, 19, 42))
    draw = ImageDraw.Draw(image)
    for index in range(14):
        color = (rng.randint(80, 200), rng.randint(90, 220), rng.randint(160, 255))
        x, y = rng.randint(-80, 600), rng.randint(-80, 360)
        radius = rng.randint(30, 160)
        draw.ellipse((x, y, x + radius, y + radius), outline=color, width=3)
    draw.rectangle((40, 330, 600, 360), fill=(143, 136, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _text_bytes(title: str) -> bytes:
    lines = [
        title,
        "=" * len(title),
        "",
        "Document de démonstration généré pour C-Tech Archives.",
        "Il illustre l’aperçu texte, le stockage privé et le contrôle SHA-256.",
        "",
    ]
    lines += [f"{index:02d}. Point d’ordre du jour n°{index}" for index in range(1, 16)]
    return "\n".join(lines).encode("utf-8")


def _add_years(day, years):
    try:
        return day.replace(year=day.year + years)
    except ValueError:  # 29 février
        return day.replace(year=day.year + years, day=28)


def _retention_dates(rng, document_date, today):
    """Calendrier crédible : quelques échéances dépassées ou proches."""
    roll = rng.random()
    if roll < 0.12:
        retention_until = today - timedelta(days=rng.randint(3, 160))
    elif roll < 0.24:
        retention_until = today + timedelta(days=rng.randint(5, 85))
    elif roll < 0.85:
        retention_until = _add_years(document_date, rng.choice((1, 5, 5, 10, 10, 30)))
    else:
        retention_until = None
    if retention_until and retention_until < document_date:
        retention_until = document_date
    review_date = None
    if rng.random() < 0.5:
        review_date = today + timedelta(days=rng.randint(-40, 120))
        if retention_until and review_date > retention_until:
            review_date = None
    return review_date, retention_until


class Command(BaseCommand):
    help = "Crée un jeu de démonstration (comptes, référentiels, archives, journal). Hors production."

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Mot de passe des comptes de démonstration.")
        parser.add_argument("--archives", type=int, default=42, help="Nombre d’archives à créer.")

    def handle(self, *args, **options):
        if settings.DJANGO_ENV == "production":
            raise CommandError("seed_demo est désactivé en production.")
        password = options["password"] or os.environ.get("CTECH_DEMO_PASSWORD")
        if not password:
            raise CommandError("Fournissez --password ou CTECH_DEMO_PASSWORD.")
        try:
            validate_password(password)
        except ValidationError as error:
            raise CommandError("Le mot de passe de démonstration est trop faible.") from error

        with transaction.atomic():
            users = self._users(password)
            services = [Service.objects.get_or_create(name=name)[0] for name in SERVICES]
            categories = [Category.objects.get_or_create(name=name)[0] for name in CATEGORIES]
            types = [DocumentType.objects.get_or_create(name=name)[0] for name in DOCUMENT_TYPES]
            created = self._archives(options["archives"], users, services, categories, types)
            events = self._audit_trail(users) if created else 0

        self.stdout.write(
            self.style.SUCCESS(
                f"Démonstration prête : {len(users)} comptes, {created} archives créées, "
                f"{events} événements d’audit."
            )
        )
        for email, *_ in DEMO_USERS:
            self.stdout.write(f"  · {email}")
        if created:
            self.stdout.write(
                f"  · {TAMPERED_REFERENCE} a un fichier volontairement altéré : "
                "sa vérification d’intégrité déclenche une alerte."
            )

    def _users(self, password):
        user_model = get_user_model()
        users = []
        for email, first_name, last_name, role in DEMO_USERS:
            user, created = user_model.objects.get_or_create(
                email=email,
                defaults={
                    "username": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": role,
                },
            )
            if created:
                user.set_password(password)
                user.save(update_fields=["password"])
            users.append(user)
        return users

    def _archives(self, count, users, services, categories, types):
        rng = random.Random(2026)
        now = timezone.now()
        today = timezone.localdate()
        uploaders = [user for user in users if user.role != Role.CONSULTANT]
        levels = [level for level, weight in LEVEL_WEIGHTS for _ in range(weight)]
        created = 0
        for index in range(1, count + 1):
            reference = f"CT-DEMO-{index:04d}"
            if Archive.objects.filter(reference=reference).exists():
                continue
            age = timedelta(days=rng.randint(0, 350), hours=rng.randint(0, 23))
            year = (now - age).year
            title = rng.choice(TITLES).format(year=year)
            level = rng.choice(levels)
            document_date = (now - age - timedelta(days=rng.randint(0, 40))).date()
            review_date, retention_until = _retention_dates(rng, document_date, today)
            archive = Archive(
                reference=reference,
                title=title,
                description=(
                    f"{title}. Pièce de démonstration rattachée au service "
                    "concerné, conservée dans le stockage privé."
                ),
                category=rng.choice(categories),
                document_type=rng.choice(types),
                service=services[min(int(rng.expovariate(0.55)), len(services) - 1)],
                uploaded_by=rng.choice(uploaders),
                document_date=document_date,
                review_date=review_date,
                retention_until=retention_until,
                status=ArchiveStatus.ARCHIVED if rng.random() < 0.28 else ArchiveStatus.ACTIVE,
                confidentiality_level=level,
            )
            kind = rng.random()
            if kind < 0.55:
                content, extension = _pdf_bytes(title, rng), "pdf"
            elif kind < 0.72:
                content, extension = _png_bytes(index), "png"
            elif kind < 0.86:
                content, extension = _text_bytes(title), "txt"
            else:
                content, extension = b"", ""
            if content:
                archive.file.save(f"demo.{extension}", ContentFile(content), save=False)
                archive.file_size = len(content)
            archive.save()
            if content:
                archive.checksum = calculate_archive_checksum(archive)
                with archive.file.open("rb") as handle:
                    archive.content_text = extract_text(handle, archive.file.name)
                archive.save(update_fields=["checksum", "content_text"])
                if reference == TAMPERED_REFERENCE:
                    with archive.file.storage.open(archive.file.name, "ab") as handle:
                        handle.write(b"\n% simulated tampering\n")
            update_search_document(archive.pk)
            Archive.objects.filter(pk=archive.pk).update(created_at=now - age, updated_at=now - age)
            created += 1
        return created

    def _audit_trail(self, users):
        """Historique crédible sur dix-huit semaines pour le pouls du journal."""
        rng = random.Random(7)
        now = timezone.now()
        archives = list(Archive.objects.filter(reference__startswith="CT-DEMO-"))
        actions = (
            (AuditAction.LOGIN, 6),
            (AuditAction.ARCHIVE_VIEW, 9),
            (AuditAction.ARCHIVE_DOWNLOAD, 3),
            (AuditAction.ARCHIVE_INTEGRITY_CHECK, 2),
            (AuditAction.ARCHIVE_UPDATE, 1),
            (AuditAction.LOGOUT, 3),
        )
        weighted = [action for action, weight in actions for _ in range(weight)]
        visible = {
            user.pk: [
                archive
                for archive in archives
                if archive.confidentiality_level in visible_confidentiality_levels_for(user)
            ]
            for user in users
        }
        events = []
        timestamps = []
        for day in range(126):
            moment = now - timedelta(days=day)
            if moment.weekday() >= 5 and rng.random() < 0.75:
                continue
            for _ in range(rng.randint(0, 9) if rng.random() < 0.85 else 0):
                actor = rng.choice(users)
                action = rng.choice(weighted)
                if action == AuditAction.ARCHIVE_UPDATE and not can_create_archive(actor):
                    action = AuditAction.ARCHIVE_VIEW
                archive = None
                details = {"source": "web"}
                if action not in (AuditAction.LOGIN, AuditAction.LOGOUT):
                    # Le journal de démonstration respecte le RBAC réel.
                    archive = rng.choice(visible[actor.pk])
                    if action == AuditAction.ARCHIVE_INTEGRITY_CHECK:
                        details = {"result": "VALID" if archive.checksum else "MISSING_CHECKSUM"}
                    if action == AuditAction.ARCHIVE_UPDATE:
                        details = {"changed_fields": ["title"], "source": "web"}
                events.append(
                    AuditLog(
                        actor=actor,
                        actor_identifier=actor.get_username(),
                        action=action,
                        archive=archive,
                        archive_reference=archive.reference if archive else "",
                        ip_address=f"10.0.{rng.randint(0, 3)}.{rng.randint(2, 250)}",
                        details=details,
                    )
                )
                timestamps.append(
                    moment.replace(hour=rng.randint(8, 18), minute=rng.randint(0, 59))
                )
        created = AuditLog.objects.bulk_create(events)
        for event, timestamp in zip(created, timestamps):
            AuditLog.objects.filter(pk=event.pk).update(timestamp=min(timestamp, now))
        return len(created)
