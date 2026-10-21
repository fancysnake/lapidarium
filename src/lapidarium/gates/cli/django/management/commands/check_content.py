from __future__ import annotations

from typing import TYPE_CHECKING, override

from django.core.management.base import BaseCommand, CommandError
from pydantic import TypeAdapter

from lapidarium.gates.cli.django.services import build_services
from lapidarium.pacts.content import NotFoundError
from lapidarium.pacts.health import HealthIssueDTO
from lapidarium.pacts.outreach import DeliveryError

_ISSUES = TypeAdapter(list[HealthIssueDTO])

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    help = "List what in the published content needs a look; exit 1 if anything."

    @override
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--json", action="store_true", help="One JSON list.")
        parser.add_argument(
            "--links", action="store_true", help="Also visit syndication links."
        )
        parser.add_argument(
            "--mail", action="store_true", help="Mail the list to the profile."
        )

    @override
    def handle(self, *_args: str, **options: bool) -> None:
        health = build_services().content_health
        issues = health.check(links=options["links"])
        if options["json"]:
            self.stdout.write(_ISSUES.dump_json(issues).decode())
        else:
            for issue in issues:
                self.stdout.write(issue.line)
        if not issues:
            return
        if options["mail"]:
            try:
                health.send_digest(issues)
            except (NotFoundError, DeliveryError) as exc:
                msg = f"Could not mail the digest: {exc}"
                raise CommandError(msg) from exc
        msg = f"{len(issues)} to look at."
        raise CommandError(msg, returncode=1)
