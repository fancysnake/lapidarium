from __future__ import annotations

from typing import override

from django.core.management.base import BaseCommand, CommandError

from lapidarium.gates.cli.django.services import build_services


class Command(BaseCommand):
    help = "Fetch FEED_SOURCES and link items to the entries they copy."

    @override
    def handle(self, *_args: str, **_options: str) -> None:
        result = build_services().feed_sync.sync()
        self.stdout.write(
            f"Fetched {result.fetched} items: {result.created} new,"
            f" {result.linked} linked to entries."
        )
        if result.failed:
            msg = "Could not read: " + ", ".join(result.failed)
            raise CommandError(msg)
