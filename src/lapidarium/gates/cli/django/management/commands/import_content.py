from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, override

from django.core.management.base import BaseCommand, CommandError

from lapidarium.gates.cli.django.services import build_services, check_demo, counts
from lapidarium.pacts.content import BundleValidationError

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    help = (
        "Import an export (format v1) or a bundled demo: create or update types,"
        " entries, assets."
    )

    @override
    def add_arguments(self, parser: ArgumentParser) -> None:
        origin = parser.add_mutually_exclusive_group(required=True)
        origin.add_argument("source", nargs="?", type=Path)
        origin.add_argument("--demo", help="A bundled demo set, instead of a path.")

    @override
    def handle(self, *_args: str, **options: Path | str | None) -> None:
        importer = build_services().content.importer
        demo = options["demo"]
        if isinstance(demo, str):
            check_demo(demo, importer.demo_names())
        try:
            summary = (
                importer.load_demo(demo)
                if isinstance(demo, str)
                else importer.import_from(Path(str(options["source"])))
            )
        except BundleValidationError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Imported {counts(summary)}."))
