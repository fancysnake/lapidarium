"""What in the published content needs a look: things that check themselves."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from lapidarium.mills.catalogue import Catalogue, ends_at, entry_ref, shows_door
from lapidarium.pacts.content import NotFoundError, Outcome
from lapidarium.pacts.health import HealthIssueDTO, HealthProblem
from lapidarium.pacts.schema import CONTAINER_ROLES, TypeRole
from lapidarium.pacts.services import ContentHealthServiceProtocol
from lapidarium.specs import STALE_AFTER

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Callable, Sequence

    from lapidarium.pacts.content import (
        EntryDTO,
        EntryRepositoryProtocol,
        ProfileRepositoryProtocol,
    )
    from lapidarium.pacts.health import LinkCheckerProtocol
    from lapidarium.pacts.outreach import MailerProtocol
    from lapidarium.pacts.schema import EntryTypeRepositoryProtocol


def _issue(
    code: HealthProblem, message: str, *, entry: EntryDTO | None = None
) -> HealthIssueDTO:
    return HealthIssueDTO(
        code=code, message=message, entry=entry_ref(entry) if entry else None
    )


class ContentHealthService(ContentHealthServiceProtocol):
    def __init__(
        self,
        *,
        types: EntryTypeRepositoryProtocol,
        entries: EntryRepositoryProtocol,
        profile: ProfileRepositoryProtocol,
        mailer: MailerProtocol,
        checker: LinkCheckerProtocol,
        clock: Callable[[], dt.datetime],
    ) -> None:
        self._types = types
        self._entries = entries
        self._profile = profile
        self._mailer = mailer
        self._checker = checker
        self._clock = clock

    @override
    def check(self, *, links: bool) -> list[HealthIssueDTO]:
        catalogue = Catalogue(self._types.list_all(), self._entries.list_published())
        issues = [
            _issue(
                HealthProblem.SMALL_DOOR,
                f"The {t.label_plural} door has too few entries to show.",
            )
            for t in catalogue.types.values()
            if t.door_enabled and not shows_door(t, catalogue.of_type(t.key))
        ]
        for entry in catalogue.entries:
            issues.extend(self._entry_issues(catalogue, entry))
        if links:
            issues.extend(
                _issue(
                    HealthProblem.DEAD_LINK, f"{link.url} does not answer.", entry=entry
                )
                for entry in catalogue.entries
                for link in entry.syndication
                if not self._checker.is_alive(link.url)
            )
        return issues

    def _entry_issues(
        self, catalogue: Catalogue, entry: EntryDTO
    ) -> list[HealthIssueDTO]:
        role = catalogue.types[entry.type_key].role
        contents = catalogue.contents(entry)
        issues: list[HealthIssueDTO] = []
        if role in CONTAINER_ROLES and not contents:
            issues.append(
                _issue(
                    HealthProblem.EMPTY_CONTAINER,
                    "This container holds nothing.",
                    entry=entry,
                )
            )
        if (
            role == TypeRole.CALENDAR
            and self._is_over(entry)
            and all(
                catalogue.types[e.type_key].role == role
                for e in catalogue.neighbours(entry)
            )
        ):
            issues.append(
                _issue(
                    HealthProblem.UNLINKED_PAST,
                    "It is over and nothing from it is linked.",
                    entry=entry,
                )
            )
        if entry.featured and entry.cover is None:
            issues.append(
                _issue(
                    HealthProblem.MISSING_COVER,
                    "Featured, but has no cover.",
                    entry=entry,
                )
            )
        if role == TypeRole.CONTAINER_OUTCOME and entry.outcome == Outcome.ONGOING:
            latest = max(e.updated_at for e in (entry, *contents))
            if self._clock() - latest > STALE_AFTER:
                issues.append(
                    _issue(
                        HealthProblem.STALE_ONGOING,
                        "Ongoing, but nothing new for months.",
                        entry=entry,
                    )
                )
        return issues

    def _is_over(self, entry: EntryDTO) -> bool:
        end = ends_at(entry)
        return end is not None and end < self._clock()

    @override
    def send_digest(self, issues: Sequence[HealthIssueDTO]) -> None:
        profile = self._profile.get()
        if profile is None or not profile.email:
            msg = "profile e-mail"
            raise NotFoundError(msg)
        self._mailer.send(
            {
                "subject": f"Content health: {len(issues)} to look at",
                "body": "\n".join(issue.line for issue in issues),
                "to": profile.email,
                "reply_to": profile.email,
            }
        )
