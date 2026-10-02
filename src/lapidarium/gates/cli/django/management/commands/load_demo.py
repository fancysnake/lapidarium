from __future__ import annotations

from typing import TYPE_CHECKING, override

from django.core.management.base import BaseCommand, CommandError

from lapidarium.gates.cli.django.services import build_services
from lapidarium.pacts import BundleValidationError

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    help = "Load a bundled demo content set (types, entries, assets) to start from."

    @override
    def add_arguments(self, parser: ArgumentParser) -> None:
        names = build_services().content_import.demo_names()
        parser.add_argument("name", choices=names)

    @override
    def handle(self, *_args: str, **options: str) -> None:
        try:
            summary = build_services().content_import.load_demo(options["name"])
        except BundleValidationError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {summary.types} types, {summary.entries} entries,"
                f" {summary.assets} assets."
            )
        )
