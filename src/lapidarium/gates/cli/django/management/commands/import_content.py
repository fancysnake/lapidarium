from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, override

from django.core.management.base import BaseCommand, CommandError

from lapidarium.gates.cli.django.services import build_services
from lapidarium.pacts import BundleValidationError

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    help = "Import an export (format v1): create or update types, entries, assets."

    @override
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("source", type=Path)

    @override
    def handle(self, *_args: str, **options: Path) -> None:
        try:
            summary = build_services().content_import.import_from(options["source"])
        except BundleValidationError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {summary.types} types, {summary.entries} entries,"
                f" {summary.assets} assets."
            )
        )
