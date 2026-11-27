from unittest.mock import MagicMock

import pytest

from lapidarium.mills.editing import EditingService
from lapidarium.pacts.content import EntryStatus, NotFoundError, RelationRole
from lapidarium.specs import DESK_RECENT, PANEL_PAGE_SIZE
from tests.factories import entry_dto, relation_dto, type_dto


def _service(entries, types=("session", "song")):
    type_repo = MagicMock()
    type_repo.list_all.return_value = [type_dto(key) for key in types]
    type_repo.entry_counts.return_value = {
        key: sum(entry.type_key == key for entry in entries) for key in types
    }
    entry_repo = MagicMock()
    entry_repo.list_all.return_value = list(entries)
    return EditingService(types=type_repo, entries=entry_repo)


def _draft(slug, type_key="session", **overrides):
    return entry_dto(slug, type_key, status=EntryStatus.DRAFT, **overrides)


def test_desk_splits_drafts_from_the_latest_published_entries():
    published = [entry_dto(f"done-{index}") for index in range(DESK_RECENT + 1)]
    entries = [_draft("first"), *published, _draft("second", "song")]

    desk = _service(entries).desk()

    assert [row.entry.slug for row in desk.drafts] == ["first", "second"]
    assert [row.entry_type.key for row in desk.drafts] == ["session", "song"]
    assert [row.entry for row in desk.published] == published[:DESK_RECENT]
    assert desk.total == len(entries)


def test_rows_name_the_containers_an_entry_is_part_of():
    entry = entry_dto(
        "moose",
        relations=(
            relation_dto(RelationRole.PART_OF, "campaign", type_key="project"),
            relation_dto(RelationRole.RELATED, "other"),
        ),
    )

    (row,) = _service([entry]).entries(type_key="", status=None, query="", page=1).rows

    assert [(ref.type_key, ref.slug) for ref in row.containers] == [
        ("project", "campaign")
    ]


def test_entries_filter_by_type_title_and_status_and_count_both_statuses():
    entries = [
        entry_dto("a", title="Castle ball"),
        _draft("b", title="Castle siege"),
        entry_dto("c", title="Forest"),
        entry_dto("d", "song", title="Castle song"),
    ]

    found = _service(entries).entries(
        type_key="session", status=EntryStatus.DRAFT, query="  cAsTle ", page=1
    )

    assert [row.entry.slug for row in found.rows] == ["b"]
    assert (found.total, found.published, found.drafts) == (2, 1, 1)
    assert (found.entry_type.key, found.status, found.query) == (
        "session",
        EntryStatus.DRAFT,
        "cAsTle",
    )
    assert [(count.entry_type.key, count.entries) for count in found.types] == [
        ("session", 3),
        ("song", 1),
    ]


def test_entries_come_in_pages():
    entries = [entry_dto(f"e-{index}") for index in range(PANEL_PAGE_SIZE + 1)]
    service = _service(entries)

    first = service.entries(type_key="", status=None, query="", page=1)
    last = service.entries(type_key="", status=None, query="", page=2)

    assert (first.page, first.pages, len(first.rows)) == (1, 2, PANEL_PAGE_SIZE)
    assert [row.entry.slug for row in last.rows] == [f"e-{PANEL_PAGE_SIZE}"]


@pytest.mark.parametrize(
    ("type_key", "page"), (("ghost", 1), ("", 0), ("", 2), ("session", 2))
)
def test_entries_refuse_an_unknown_type_and_a_page_out_of_range(type_key, page):
    service = _service([entry_dto("a")])

    with pytest.raises(NotFoundError):
        service.entries(type_key=type_key, status=None, query="", page=page)
