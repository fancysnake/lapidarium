from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, Unpack, override

from django.core.management.base import BaseCommand, CommandError

from lapidarium.gates.cli.django.services import build_services
from lapidarium.pacts.content import ArchiveError, BundleValidationError

if TYPE_CHECKING:
    from argparse import ArgumentParser


class _Options(TypedDict):
    destination: Path
    commit: bool
    push: bool


class Command(BaseCommand):
    help = "Export published content, its types and assets as format v1."

    @override
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("destination", type=Path)
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Commit the export; the destination must be a git working copy.",
        )
        parser.add_argument(
            "--push", action="store_true", help="Push the commit, if there is one."
        )

    @override
    def handle(self, *_args: str, **options: Unpack[_Options]) -> None:
        try:
            result = build_services().content_export.export(
                options["destination"], commit=options["commit"], push=options["push"]
            )
        except (BundleValidationError, ArchiveError) as exc:
            raise CommandError(str(exc)) from exc
        summary = result.content
        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {summary.types} types, {summary.entries} entries,"
                f" {summary.assets} assets."
                + (" Committed." if result.committed else "")
            )
        )
