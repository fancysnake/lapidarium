from __future__ import annotations

from typing import TYPE_CHECKING, override

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from lapidarium.gates.cli.django.services import build_services, check_demo, counts
from lapidarium.pacts.content import BundleValidationError

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    help = "Migrate, load a demo and ensure an admin login. Refused unless DEBUG."

    @override
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--demo", default="ttrpg")
        parser.add_argument("--username", default="admin")
        parser.add_argument("--password", default="admin")

    @override
    def handle(self, *_args: str, **options: str) -> None:
        if not settings.DEBUG:
            msg = "Local setup creates a known login; it runs only with DEBUG on."
            raise CommandError(msg)
        content = build_services().content
        check_demo(options["demo"], content.importer.demo_names())
        call_command("migrate", verbosity=0)
        try:
            result = content.local_setup.set_up(
                options["demo"],
                username=options["username"],
                password=options["password"],
            )
        except BundleValidationError as exc:
            raise CommandError(str(exc)) from exc
        verb = "Created" if result.superuser_created else "Reset"
        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {counts(result.content)}. {verb} superuser"
                f" {options['username']!r}."
            )
        )
