import datetime as dt
from operator import itemgetter
from unittest.mock import MagicMock

import pytest

from lapidarium.mills.site import SiteService
from lapidarium.pacts.site import (
    FriendDTO,
    LinkDTO,
    MaintenanceDTO,
    MaintenanceNoticeDTO,
    TypeColourDTO,
)
from tests.factories import profile_dto, type_dto

PROFILE = profile_dto()
LINK = LinkDTO(platform="itch", url="https://example.itch.io", label="itch.io")
FRIEND = FriendDTO(name="Ada", url="https://ada.example.org", button=None)
NOW = dt.datetime(2026, 10, 14, 12, tzinfo=dt.UTC)
HOUR = dt.timedelta(hours=1)
MAINTENANCE = MaintenanceDTO(
    enabled=True,
    starts_at=NOW - HOUR,
    ends_at=NOW + HOUR,
    reasons=("feeding the mimics", "identifying player tribes"),
)


def _service(*, types=(), profile=PROFILE, dark_colours=None, maintenance=None):
    repos = MagicMock()
    repos.types.list_all.return_value = list(types)
    repos.profile.get.return_value = profile
    repos.profile.list_links.return_value = [LINK]
    repos.profile.list_friends.return_value = [FRIEND]
    repos.maintenance.get.return_value = maintenance
    schema = MagicMock()
    schema.derive_dark_colour.side_effect = (dark_colours or {}).get
    rng = MagicMock()
    rng.choice.side_effect = itemgetter(-1)
    return SiteService(
        types=repos.types,
        profile=repos.profile,
        maintenance=repos.maintenance,
        schema=schema,
        site_name="Lapidarium",
        clock=lambda: NOW,
        rng=rng,
    )


def test_chrome_gives_profile_menu_and_types():
    session = type_dto("session", colour="#6b3fa0", tint="#f3eef9")
    wiki = type_dto("wiki", colour="#0f6b5f", tint="", in_menu=False)

    site = _service(types=[session, wiki]).chrome()

    assert site.profile == PROFILE
    assert site.owner_name == "Mira"
    assert site.links == (LINK,)
    assert site.types == (session, wiki)
    assert site.menu == (session,)
    assert site.dark_colours == ()


def test_chrome_gives_the_dark_colours_that_differ():
    session = type_dto("session", colour="#6b3fa0", tint="")
    wiki = type_dto("wiki", colour="#c9a0ff", tint="")
    darks = {"#6b3fa0": "#9779bc", "#c9a0ff": "#c9a0ff"}

    site = _service(types=[session, wiki], dark_colours=darks).chrome()

    assert site.dark_colours == (TypeColourDTO(key="session", colour="#9779bc"),)


@pytest.mark.parametrize("profile", (None, PROFILE.model_copy(update={"name": ""})))
def test_chrome_names_the_site_when_the_profile_names_no_one(profile):
    assert _service(profile=profile).chrome().owner_name == "Lapidarium"


def test_friends_are_those_the_profile_keeps():
    assert _service().friends() == (FRIEND,)


def test_maintenance_shows_a_random_reason_and_the_wait_until_its_end():
    notice = _service(maintenance=MAINTENANCE).maintenance()

    assert notice == MaintenanceNoticeDTO(
        profile=PROFILE,
        owner_name="Mira",
        starts_at=NOW - HOUR,
        ends_at=NOW + HOUR,
        reason="identifying player tribes",
        retry_after=3600,
    )


def test_maintenance_without_end_or_reasons_gives_no_wait_and_no_reason():
    state = MAINTENANCE.model_copy(update={"ends_at": None, "reasons": ()})

    notice = _service(maintenance=state, profile=None).maintenance()

    assert notice is not None
    assert notice.owner_name == "Lapidarium"
    assert (notice.ends_at, notice.reason, notice.retry_after) == (None, "", None)


def test_maintenance_rounds_the_wait_up_to_a_whole_second():
    state = MAINTENANCE.model_copy(update={"ends_at": NOW + dt.timedelta(seconds=0.2)})

    notice = _service(maintenance=state).maintenance()

    assert notice is not None
    assert notice.retry_after == 1


@pytest.mark.parametrize(
    "state",
    (
        None,
        MAINTENANCE.model_copy(update={"enabled": False}),
        MAINTENANCE.model_copy(update={"starts_at": NOW + HOUR}),
        MAINTENANCE.model_copy(update={"ends_at": NOW}),
    ),
    ids=("never-set", "off", "not-started", "ended"),
)
def test_maintenance_leaves_the_site_live_outside_its_window(state):
    assert _service(maintenance=state).maintenance() is None
