from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, override

from django.core.management.base import BaseCommand, CommandError

from lapidarium.gates.cli.django.services import build_services
from lapidarium.pacts.content import BundleValidationError, ExportDTO, NotFoundError
from lapidarium.pacts.outreach import DeliveryError

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    help = "Export published content, its types and assets as format v1."

    @override
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("destination")
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Commit the export; the destination must be a git working copy.",
        )
        parser.add_argument(
            "--push", action="store_true", help="Push the commit, if there is one."
        )

    @override
    def handle(self, *_args: str, **options: str | bool) -> None:
        destination = Path(str(options["destination"]))
        export = build_services().content_export
        push = bool(options["push"])
        try:
            result = (
                export.publish(destination, push=push)
                if options["commit"] or push
                else ExportDTO(content=export.export(destination), committed=False)
            )
        except (BundleValidationError, NotFoundError, DeliveryError) as exc:
            raise CommandError(str(exc)) from exc
        summary = result.content
        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {summary.types} types, {summary.entries} entries,"
                f" {summary.assets} assets."
                + (" Committed." if result.committed else "")
            )
        )
