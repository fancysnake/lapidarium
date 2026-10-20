import datetime as dt
from unittest.mock import MagicMock

import pytest

from lapidarium.mills.health import ContentHealthService
from lapidarium.pacts.content import (
    MediaAssetDTO,
    NotFoundError,
    ProfileDTO,
    RelationRole,
    SyndicationLinkDTO,
)
from lapidarium.pacts.schema import TypeRole
from lapidarium.specs import STALE_AFTER
from tests.factories import NOW, entry_dto, ref_dto, relation_dto, type_dto

DAY = dt.timedelta(days=1)
COVER = MediaAssetDTO(path="a.png", url="/a.png", alt="A")
SESSION = type_dto("session")
EVENT = type_dto("event", role=TypeRole.CALENDAR)
PROJECT = type_dto("project", role=TypeRole.CONTAINER_OUTCOME)


def _service(*, types=(SESSION,), entries=(), email="mira@example.com", alive=True):
    deps = MagicMock()
    deps.types.list_all.return_value = list(types)
    deps.entries.list_published.return_value = list(entries)
    deps.profile.get.return_value = (
        ProfileDTO(name="M", handle="", tagline="", photo=None, bio="", email=email)
        if email is not None
        else None
    )
    deps.checker.is_alive.return_value = alive
    service = ContentHealthService(
        types=deps.types,
        entries=deps.entries,
        profile=deps.profile,
        mailer=deps.mailer,
        checker=deps.checker,
        clock=lambda: NOW,
    )
    return service, deps


def _codes(issues):
    return [(i.code, i.entry.slug if i.entry else None) for i in issues]


def test_healthy_content_has_no_issues():
    service, deps = _service(entries=[entry_dto()])

    assert service.check(links=False) == []
    deps.checker.is_alive.assert_not_called()


def test_door_without_enough_entries():
    session = type_dto("session", door_enabled=True, door_min_entries=2)
    service, _ = _service(types=[session], entries=[entry_dto()])

    assert _codes(service.check(links=False)) == [("H002", None)]


def test_empty_container_and_featured_without_cover():
    entries = [
        entry_dto("empty", "project"),
        entry_dto("star", featured=True),
        entry_dto("covered", featured=True, cover=COVER),
    ]
    service, _ = _service(types=[SESSION, PROJECT], entries=entries)

    assert _codes(service.check(links=False)) == [("H001", "empty"), ("H004", "star")]


def test_past_calendar_entries_need_something_linked():
    linked_out = entry_dto(
        "linked-out",
        "event",
        start_at=NOW - DAY,
        relations=(relation_dto(RelationRole.RELATED, "moose"),),
    )
    entries = [
        entry_dto("lonely", "event", start_at=NOW - 2 * DAY),
        entry_dto(
            "only-events",
            "event",
            start_at=NOW - 2 * DAY,
            end_at=NOW - DAY,
            relations=(relation_dto(RelationRole.RELATED, "lonely", type_key="event"),),
        ),
        linked_out,
        entry_dto("future", "event", start_at=NOW + DAY),
        entry_dto("moose"),
        entry_dto(
            "linked-in",
            relations=(
                relation_dto(RelationRole.RELATED, "upcoming-ish", type_key="event"),
            ),
        ),
    ]
    service, _ = _service(types=[SESSION, EVENT], entries=entries)

    assert _codes(service.check(links=False)) == [
        ("H003", "lonely"),
        ("H003", "only-events"),
    ]


def test_ongoing_containers_go_stale():
    old = NOW - STALE_AFTER - DAY
    entries = [
        entry_dto("stale", "project", outcome="ongoing", updated_at=old),
        entry_dto("fresh", "project", outcome="ongoing", updated_at=old),
        entry_dto("done", "project", outcome="finished", updated_at=old),
        *(
            entry_dto(
                f"part-{slug}",
                updated_at=when,
                relations=(
                    relation_dto(RelationRole.PART_OF, slug, type_key="project"),
                ),
            )
            for slug, when in (("stale", old), ("fresh", NOW), ("done", old))
        ),
    ]
    service, _ = _service(types=[SESSION, PROJECT], entries=entries)

    assert _codes(service.check(links=False)) == [("H005", "stale")]


def test_dead_syndication_links_only_when_asked():
    link = SyndicationLinkDTO(platform="youtube", url="https://youtu.be/gone")
    service, deps = _service(entries=[entry_dto(syndication=(link,))], alive=False)

    assert service.check(links=False) == []
    issues = service.check(links=True)

    assert _codes(issues) == [("H006", "moose")]
    assert issues[0].message == "https://youtu.be/gone does not answer."
    deps.checker.is_alive.assert_called_once_with("https://youtu.be/gone")


def test_digest_mails_the_profile():
    service, deps = _service(
        types=[type_dto(door_enabled=True, door_min_entries=2), PROJECT],
        entries=[entry_dto("empty", "project")],
    )
    issues = service.check(links=False)

    service.send_digest(issues)

    deps.mailer.send.assert_called_once_with(
        {
            "subject": "Content health: 2 to look at",
            "body": (
                "[H002] The Sessions door has too few entries to show.\n"
                "[H001] project/empty: This container holds nothing."
            ),
            "to": "mira@example.com",
            "reply_to": "mira@example.com",
        }
    )


@pytest.mark.parametrize("email", ("", None))
def test_digest_needs_an_address(email):
    service, deps = _service(email=email)

    with pytest.raises(NotFoundError):
        service.send_digest([])
    deps.mailer.send.assert_not_called()


def test_refs_point_at_the_entry():
    service, _ = _service(types=[PROJECT], entries=[entry_dto("empty", "project")])

    assert service.check(links=False)[0].entry == ref_dto("empty", "project")
