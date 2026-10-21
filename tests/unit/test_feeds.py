import datetime as dt
from unittest.mock import MagicMock

import pytest

from lapidarium.mills.feeds import FeedSyncService, same_page
from lapidarium.pacts.content import EntryKeyDTO, SyndicationLinkDTO
from lapidarium.pacts.feeds import FeedError, FeedSyncDTO
from tests.factories import NOW, entry_dto

VIDEO = "https://www.youtube.com/watch?v=abc"


@pytest.mark.parametrize(
    ("first", "second"),
    (
        ("https://www.example.com/a?x=1", "http://example.com/a?x=1"),
        ("https://m.example.com/a", "https://example.com/a/"),
        ("https://example.com/a/?x=1&y=2", "https://example.com/a?y=2&x=1"),
    ),
)
def test_same_page_ignores_what_does_not_name_the_page(first, second):
    assert same_page(first) == same_page(second)


def test_different_pages_differ():
    assert same_page("https://example.com/a") != same_page("https://example.com/b")


def _item(url, external_id="1"):
    return {
        "source": "YouTube",
        "external_id": external_id,
        "title": "Video",
        "url": url,
        "published_at": NOW - dt.timedelta(days=1),
        "thumbnail_url": "",
    }


def test_sync_saves_items_and_links_copies_of_entries():
    deps = MagicMock()
    deps.entries.list_published.return_value = [
        entry_dto(
            "moose",
            syndication=(
                SyndicationLinkDTO(platform="youtube", url="https://youtu.be/abc"),
            ),
        )
    ]
    good, broken = MagicMock(), MagicMock()
    good.fetch.return_value = [_item(VIDEO), _item("https://youtu.be/other", "2")]
    broken.fetch.side_effect = FeedError
    broken.name = "GitHub owner/repo"
    deps.external.save.side_effect = [True, False]
    service = FeedSyncService(
        sources=[good, broken],
        external=deps.external,
        entries=deps.entries,
        transaction=deps.transaction,
    )

    result = service.sync()

    assert result == FeedSyncDTO(
        fetched=2, created=1, linked=1, failed=("GitHub owner/repo",)
    )
    assert deps.external.save.call_args_list[0].kwargs == {
        "entry": EntryKeyDTO(type_key="session", slug="moose")
    }
    assert deps.external.save.call_args_list[1].kwargs == {"entry": None}
    deps.transaction.atomic.assert_called_once_with()


@pytest.mark.parametrize(
    "link",
    (
        "https://youtu.be/abc?si=share",
        "https://www.youtube.com/shorts/abc",
        "https://www.youtube.com/live/abc",
        "https://m.youtube.com/watch?v=abc&t=10",
    ),
)
def test_sync_links_a_youtube_video_by_its_id(link):
    deps = MagicMock()
    deps.entries.list_published.return_value = [
        entry_dto(
            "moose", syndication=(SyndicationLinkDTO(platform="youtube", url=link),)
        )
    ]
    source = MagicMock()
    source.fetch.return_value = [_item(VIDEO)]
    service = FeedSyncService(
        sources=[source],
        external=deps.external,
        entries=deps.entries,
        transaction=deps.transaction,
    )

    assert service.sync().linked == 1
    deps.external.save.assert_called_once_with(
        _item(VIDEO), entry=EntryKeyDTO(type_key="session", slug="moose")
    )
