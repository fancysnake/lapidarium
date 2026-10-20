import datetime as dt
from operator import itemgetter
from unittest.mock import MagicMock

import pytest

from lapidarium.mills.catalogue import Catalogue, CatalogueService, when
from lapidarium.pacts.catalogue import CardDTO, FactDTO, FeedChange, FilterDTO
from lapidarium.pacts.content import NotFoundError, RelationRole
from lapidarium.pacts.feeds import ExternalItemDTO
from lapidarium.pacts.schema import DoorPick, FieldKind, TypeRole
from lapidarium.specs import PAGE_SIZE, SEARCH_LIMIT, WHATS_NEW_HOME
from tests.factories import NOW, entry_dto, field_dto, ref_dto, relation_dto, type_dto

DAY = dt.timedelta(days=1)
SESSION = type_dto(
    "session",
    route="sessions",
    fields=(
        field_dto("system", show_on_card=True),
        field_dto("players", show_in_metadata_panel=False),
    ),
)
SONG = type_dto(
    "song",
    route="songs",
    fields=(
        field_dto(
            "inspired_by", FieldKind.RELATION, target_type="session", show_on_card=True
        ),
    ),
)
EVENT = type_dto("event", route="events", role=TypeRole.CALENDAR)
PROJECT = type_dto("project", route="projects", role=TypeRole.CONTAINER_OUTCOME)


def _service(*, types=(SESSION,), entries=(), external=(), rng=None):
    repos = MagicMock()
    repos.types.list_all.return_value = list(types)
    repos.entries.list_published.return_value = list(entries)
    repos.entries.search.return_value = list(entries)
    repos.external.list_recent.return_value = list(external)
    service = CatalogueService(
        types=repos.types,
        entries=repos.entries,
        external=repos.external,
        clock=lambda: NOW,
        rng=rng or MagicMock(),
    )
    return service, repos


def _card(entry, *, entry_type=SESSION, facts=()):
    return CardDTO(entry=entry, entry_type=entry_type, facts=facts)


def _event(slug, *, days, length=None):
    start = NOW + days * DAY
    return entry_dto(
        slug, "event", start_at=start, end_at=start + length if length else None
    )


def test_when_prefers_the_date():
    entry = entry_dto(date=dt.date(2026, 3, 14), start_at=NOW)

    assert when(entry) == dt.date(2026, 3, 14)


def test_when_falls_back_to_the_start():
    assert when(entry_dto(start_at=NOW)) == NOW.date()


def test_when_is_none_without_either():
    assert when(entry_dto()) is None


def test_catalogue_unknown_types_entries_are_left_out():
    catalogue = Catalogue([SESSION], [entry_dto("a"), entry_dto("b", "ghost")])

    assert [e.slug for e in catalogue.entries] == ["a"]


def test_catalogue_unknown_route_is_not_found():
    with pytest.raises(NotFoundError):
        Catalogue([SESSION], []).by_route("nope")


def test_catalogue_card_shows_card_fields_with_values():
    entry = entry_dto(metadata={"system": "Mothership", "players": "Ania"})

    card = Catalogue([SESSION], [entry]).card(entry)

    assert card == _card(
        entry,
        facts=(
            FactDTO(label="System", kind=FieldKind.TEXT, value="Mothership", refs=()),
        ),
    )


def test_catalogue_blank_values_are_no_facts():
    entry = entry_dto(metadata={"system": ""})

    assert Catalogue([SESSION], [entry]).card(entry).facts == ()


def test_catalogue_relation_fields_list_published_targets():
    session = entry_dto("moose")
    song = entry_dto(
        "ballad",
        "song",
        relations=(
            relation_dto("inspired_by", "moose"),
            relation_dto("inspired_by", "draft"),
        ),
    )

    card = Catalogue([SESSION, SONG], [session, song]).card(song)

    assert card.facts == (
        FactDTO(
            label="Inspired_By",
            kind=FieldKind.RELATION,
            value=None,
            refs=(ref_dto("moose"),),
        ),
    )


def test_catalogue_relation_field_without_targets_is_no_fact():
    song = entry_dto("ballad", "song")

    assert Catalogue([SESSION, SONG], [song]).card(song).facts == ()


def test_home_doors_pick_per_type_and_skip_the_rest():
    latest = entry_dto("latest", date=dt.date(2026, 5, 1))
    older = entry_dto("older", date=dt.date(2026, 3, 1), featured=True)
    types = [
        type_dto(
            "session",
            door_enabled=True,
            door_pick=DoorPick.LATEST,
            door_label="Sessions RPG",
        ),
        type_dto("song", door_enabled=True, door_pick=DoorPick.LATEST_FEATURED),
        type_dto("game", door_enabled=True, door_min_entries=2),
        type_dto("meme"),
    ]
    entries = [
        latest,
        older,
        entry_dto("hit", "song", date=dt.date(2025, 1, 1), featured=True),
        entry_dto("new", "song", date=dt.date(2026, 1, 1)),
        entry_dto("lonely", "game"),
        entry_dto("unseen", "meme"),
    ]
    service, _ = _service(types=types, entries=entries)

    doors = service.home().doors

    assert [(d.entry_type.key, d.label, d.pick.entry.slug) for d in doors] == [
        ("session", "Sessions RPG", "latest"),
        ("song", "Songs", "hit"),
    ]


def test_home_latest_featured_falls_back_to_the_latest():
    types = [type_dto(door_enabled=True, door_pick=DoorPick.LATEST_FEATURED)]
    entries = [
        entry_dto("old", date=dt.date(2025, 1, 1)),
        entry_dto("new", date=dt.date(2026, 1, 1)),
    ]
    service, _ = _service(types=types, entries=entries)

    assert service.home().doors[0].pick.entry.slug == "new"


def test_home_random_featured_draws_among_featured():
    rng = MagicMock()
    rng.choice.side_effect = itemgetter(-1)
    types = [type_dto(door_enabled=True, door_pick=DoorPick.RANDOM_FEATURED)]
    entries = [
        entry_dto("a", featured=True, date=dt.date(2026, 2, 1)),
        entry_dto("b", featured=True, date=dt.date(2026, 1, 1)),
        entry_dto("c"),
    ]
    service, _ = _service(types=types, entries=entries, rng=rng)

    assert service.home().doors[0].pick.entry.slug == "b"
    assert [e.slug for e in rng.choice.call_args.args[0]] == ["a", "b"]


def test_home_random_featured_draws_among_all_without_featured():
    rng = MagicMock()
    rng.choice.side_effect = itemgetter(0)
    types = [type_dto(door_enabled=True, door_pick=DoorPick.RANDOM_FEATURED)]
    service, _ = _service(types=types, entries=[entry_dto("a")], rng=rng)

    assert service.home().doors[0].pick.entry.slug == "a"


@pytest.mark.parametrize(
    ("events", "expected"),
    (
        ((("past", -10), ("soon", 3), ("later", 30)), "soon"),
        ((("past", -10), ("older", -20)), "past"),
    ),
)
def test_home_upcoming_door_shows_the_soonest_or_else_the_latest(events, expected):
    event_type = type_dto(
        "event", role=TypeRole.CALENDAR, door_enabled=True, door_pick="upcoming"
    )
    entries = [_event(slug, days=days) for slug, days in events]
    service, _ = _service(types=[event_type], entries=entries)

    assert service.home().doors[0].pick.entry.slug == expected


def test_home_next_up_is_the_soonest_calendar_entry_not_over():
    entries = [
        _event("over", days=-3, length=DAY),
        _event("running", days=-1, length=3 * DAY),
        _event("soon", days=2),
        entry_dto("session-today", start_at=NOW + DAY),
    ]
    service, _ = _service(types=[SESSION, EVENT], entries=entries)

    assert service.home().next_up == _card(entries[1], entry_type=EVENT)


def test_home_no_next_up_without_upcoming_entries():
    service, _ = _service(types=[EVENT], entries=[_event("over", days=-1)])

    assert service.home().next_up is None


def test_home_whats_new_is_capped_for_the_home_page():
    entries = [entry_dto(f"e{i}") for i in range(WHATS_NEW_HOME + 2)]
    service, repos = _service(entries=entries)

    assert len(service.home().whats_new) == WHATS_NEW_HOME
    repos.external.list_recent.assert_called_once_with(WHATS_NEW_HOME)


def test_whatsnew_merges_entries_and_external_items_newest_first():
    added = entry_dto("added", updated_at=NOW - 2 * DAY, created_at=NOW - 2 * DAY)
    updated = entry_dto("updated", created_at=NOW - 30 * DAY, updated_at=NOW)
    hidden = entry_dto("hidden", hide_from_whats_new=True, updated_at=NOW)
    video = ExternalItemDTO(
        source="YouTube",
        title="Stream",
        url="https://youtu.be/x",
        published_at=NOW - DAY,
    )
    service, _ = _service(entries=[added, updated, hidden], external=[video])

    items = service.whats_new()

    assert [(i.change, i.title, i.type_key, i.type_label) for i in items] == [
        (FeedChange.UPDATED, "Updated", "session", "Session"),
        (FeedChange.EXTERNAL, "Stream", "external", "YouTube"),
        (FeedChange.ADDED, "Added", "session", "Session"),
    ]
    assert items[0].entry == ref_dto("updated")
    assert not items[0].url
    assert items[1].entry is None
    assert items[1].url == "https://youtu.be/x"


def test_listing_unknown_route_is_not_found():
    service, _ = _service()

    with pytest.raises(NotFoundError):
        service.listing("nope", filters={}, page=1)


def test_listing_lists_the_types_entries_newest_first():
    entries = [
        entry_dto("old", date=dt.date(2025, 1, 1)),
        entry_dto("new", date=dt.date(2026, 1, 1)),
        entry_dto("song", "song"),
    ]
    service, _ = _service(types=[SESSION, SONG], entries=entries)

    listing = service.listing("sessions", filters={}, page=1)

    assert listing.entry_type == SESSION
    assert [c.entry.slug for c in listing.cards] == ["new", "old"]
    assert (listing.page, listing.pages, listing.total) == (1, 1, 2)
    assert listing.upcoming == ()
    assert listing.filters == ()


def test_listing_filters_offer_values_present_and_apply_the_selected():
    session = type_dto(
        route="sessions",
        list_filters=["year", "tag", "system", "nope"],
        fields=(field_dto("system"),),
    )
    entries = [
        entry_dto(
            "a",
            date=dt.date(2025, 1, 1),
            tags=("horror",),
            metadata={"system": "Mothership"},
        ),
        entry_dto("b", date=dt.date(2026, 1, 1), tags=("sci-fi", "horror")),
        entry_dto("c", metadata={"system": ""}),
    ]
    service, _ = _service(types=[session], entries=entries)

    listing = service.listing(
        "sessions", filters={"tag": "horror", "system": "Nope"}, page=1
    )

    assert listing.filters == (
        FilterDTO(key="year", label="", options=("2026", "2025"), selected=""),
        FilterDTO(key="tag", label="", options=("horror", "sci-fi"), selected="horror"),
        FilterDTO(key="system", label="System", options=("Mothership",), selected=""),
    )
    assert [c.entry.slug for c in listing.cards] == ["b", "a"]
    assert listing.total == 2


def test_listing_filtering_by_year():
    session = type_dto(route="sessions", list_filters=["year"])
    entries = [
        entry_dto("a", date=dt.date(2025, 1, 1)),
        entry_dto("b", date=dt.date(2026, 1, 1)),
    ]
    service, _ = _service(types=[session], entries=entries)

    listing = service.listing("sessions", filters={"year": "2025"}, page=1)

    assert [c.entry.slug for c in listing.cards] == ["a"]


def test_listing_calendar_types_split_upcoming_from_the_archive():
    entries = [
        _event("later", days=30),
        _event("past", days=-5),
        _event("soon", days=2),
    ]
    service, _ = _service(types=[EVENT], entries=entries)

    listing = service.listing("events", filters={}, page=1)

    assert [c.entry.slug for c in listing.upcoming] == ["soon", "later"]
    assert [c.entry.slug for c in listing.cards] == ["past"]
    assert listing.total == 3


def test_listing_pages():
    entries = [
        entry_dto(f"e{i:02}", date=dt.date(2026, 1, 1) - i * DAY)
        for i in range(PAGE_SIZE + 1)
    ]
    service, _ = _service(entries=entries)

    listing = service.listing("sessions", filters={}, page=2)

    assert [c.entry.slug for c in listing.cards] == [f"e{PAGE_SIZE:02}"]
    assert (listing.page, listing.pages) == (2, 2)


@pytest.mark.parametrize("page", (0, 2))
def test_listing_a_page_outside_the_list_is_not_found(page):
    service, _ = _service(entries=[entry_dto()])

    with pytest.raises(NotFoundError):
        service.listing("sessions", filters={}, page=page)


def test_listing_an_empty_list_has_one_page():
    service, _ = _service()

    assert service.listing("sessions", filters={}, page=1).pages == 1


def test_detail_unknown_slug_is_not_found():
    service, _ = _service()

    with pytest.raises(NotFoundError):
        service.detail("sessions", "nope")


def test_detail_list_only_types_have_no_detail_page():
    meme = type_dto("meme", route="memes", has_detail_page=False)
    service, _ = _service(types=[meme], entries=[entry_dto("x", "meme")])

    with pytest.raises(NotFoundError):
        service.detail("memes", "x")


def test_detail_gathers_panel_containers_related_and_siblings():
    moose = entry_dto(
        "moose",
        metadata={"system": "Mothership", "players": "Ania"},
        relations=(
            relation_dto(RelationRole.PART_OF, "saga", type_key="project"),
            relation_dto(RelationRole.RELATED, "ballad", type_key="song"),
            relation_dto(RelationRole.RELATED, "gone", type_key="song"),
        ),
    )
    saga = entry_dto("saga", "project")
    sibling = entry_dto(
        "sibling",
        date=dt.date(2026, 1, 1),
        relations=(relation_dto(RelationRole.PART_OF, "saga", type_key="project"),),
    )
    ballad = entry_dto(
        "ballad",
        "song",
        relations=(
            relation_dto("inspired_by", "moose"),
            relation_dto(RelationRole.RELATED, "moose"),
        ),
    )
    service, _ = _service(
        types=[SESSION, SONG, PROJECT], entries=[moose, saga, sibling, ballad]
    )

    detail = service.detail("sessions", "moose")

    assert detail.card.entry == moose
    assert detail.panel == (
        FactDTO(label="System", kind=FieldKind.TEXT, value="Mothership", refs=()),
    )
    assert detail.containers == (ref_dto("saga", "project"),)
    assert [c.entry.slug for c in detail.related] == ["ballad"]
    assert [c.entry.slug for c in detail.siblings] == ["sibling"]
    assert detail.contents == ()


def test_detail_containers_list_their_contents():
    saga = entry_dto("saga", "project")
    parts = [
        entry_dto(
            slug,
            date=day,
            relations=(relation_dto(RelationRole.PART_OF, "saga", type_key="project"),),
        )
        for slug, day in (
            ("first", dt.date(2026, 1, 1)),
            ("second", dt.date(2026, 2, 1)),
        )
    ]
    service, _ = _service(types=[SESSION, PROJECT], entries=[saga, *parts])

    detail = service.detail("projects", "saga")

    assert [c.entry.slug for c in detail.contents] == ["second", "first"]
    assert detail.related == ()
    assert detail.siblings == ()


@pytest.mark.parametrize("query", ("", " a "))
def test_search_short_queries_find_nothing(query):
    service, repos = _service()

    assert not service.search(query)
    repos.entries.search.assert_not_called()


def test_search_searches_every_word_up_to_the_limit():
    service, repos = _service(entries=[entry_dto()])

    found = service.search(" space  moose ")

    repos.entries.search.assert_called_once_with(["space", "moose"], limit=SEARCH_LIMIT)
    assert found == (_card(entry_dto()),)


def test_search_cards_keep_relations_to_entries_that_did_not_match():
    moose = entry_dto()
    ballad = entry_dto(
        "ballad", "song", relations=(relation_dto("inspired_by", "moose"),)
    )
    meme = entry_dto("x", "meme")
    service, repos = _service(types=[SESSION, SONG], entries=[moose, ballad, meme])
    repos.entries.search.return_value = [ballad, meme]

    found = service.search("ballad")

    assert found == (
        _card(
            ballad,
            entry_type=SONG,
            facts=(
                FactDTO(
                    label="Inspired_By",
                    kind=FieldKind.RELATION,
                    value=None,
                    refs=(ref_dto("moose"),),
                ),
            ),
        ),
    )


def test_timeline_lists_containers_newest_first():
    initiative = type_dto("initiative", role=TypeRole.CONTAINER_TIMESPAN)
    entries = [
        entry_dto("old", "initiative", start_at=NOW - 900 * DAY),
        entry_dto("new", "project", start_at=NOW),
        entry_dto("session"),
    ]
    service, _ = _service(types=[SESSION, PROJECT, initiative], entries=entries)

    assert [c.entry.slug for c in service.timeline()] == ["new", "old"]


def test_upcoming_lists_calendar_entries_soonest_first():
    entries = [_event("later", days=9), _event("past", days=-1), _event("soon", days=1)]
    service, _ = _service(types=[EVENT], entries=entries)

    assert [c.entry.slug for c in service.upcoming()] == ["soon", "later"]
