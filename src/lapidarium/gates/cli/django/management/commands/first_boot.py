from __future__ import annotations

from typing import override

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from lapidarium.gates.cli.django.services import build_services
from lapidarium.pacts.content import BundleValidationError


class Command(BaseCommand):
    help = "Load DEMO_CONTENT and create the admin on a database nobody has used."

    @override
    def handle(self, *_args: str, **_options: str) -> None:
        services = build_services()
        demo = settings.DEMO_CONTENT
        names = services.content_import.demo_names()
        if demo and demo not in names:
            msg = f"DEMO_CONTENT {demo!r}: not one of {', '.join(names)}."
            raise CommandError(msg)
        try:
            result = services.first_boot.run(
                demo, username=settings.ADMIN_USERNAME, password=settings.ADMIN_PASSWORD
            )
        except BundleValidationError as exc:
            raise CommandError(str(exc)) from exc
        if content := result.content:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Loaded {content.types} types, {content.entries} entries,"
                    f" {content.assets} assets."
                )
            )
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
