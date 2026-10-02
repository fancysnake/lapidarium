from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, override

from django.core.management.base import BaseCommand

from lapidarium.gates.cli.django.services import build_services

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    help = "Export published content, its types and assets as format v1."

    @override
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("destination", type=Path)

    @override
    def handle(self, *_args: str, **options: Path) -> None:
        summary = build_services().content_export.export(options["destination"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {summary.types} types, {summary.entries} entries,"
                f" {summary.assets} assets."
            )
        )
