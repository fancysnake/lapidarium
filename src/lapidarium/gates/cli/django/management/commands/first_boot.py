from __future__ import annotations

from typing import override

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from lapidarium.gates.cli.django.services import build_services, counts
from lapidarium.pacts.content import BundleValidationError, NotFoundError


class Command(BaseCommand):
    help = "Load DEMO_CONTENT and create the admin on a database nobody has used."

    @override
    def handle(self, *_args: str, **_options: str) -> None:
        services = build_services()
        demo = settings.DEMO_CONTENT
        try:
            result = services.first_boot.run(
                demo, username=settings.ADMIN_USERNAME, password=settings.ADMIN_PASSWORD
            )
        except BundleValidationError as exc:
            raise CommandError(str(exc)) from exc
        except NotFoundError as exc:
            names = ", ".join(services.content_import.demo_names())
            msg = f"DEMO_CONTENT {demo!r}: not one of {names}."
            raise CommandError(msg) from exc
        if content := result.content:
            self.stdout.write(self.style.SUCCESS(f"Loaded {counts(content)}."))
        else:
            self.stdout.write("No demo loaded.")
        if result.superuser_created:
            self.stdout.write(
                self.style.SUCCESS(f"Created superuser {settings.ADMIN_USERNAME!r}.")
            )
        else:
            self.stdout.write(
                "No superuser created: an account exists or ADMIN_PASSWORD is empty."
            )
