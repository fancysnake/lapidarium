"""Items published elsewhere, pulled in and tied to the entries they copy."""

from __future__ import annotations

from typing import TYPE_CHECKING, override
from urllib.parse import parse_qsl, urlencode, urlsplit

from lapidarium.mills.video import youtube_id
from lapidarium.pacts.content import EntryKeyDTO
from lapidarium.pacts.feeds import FeedError, FeedSyncDTO
from lapidarium.pacts.services import FeedSyncServiceProtocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lapidarium.pacts.content import EntryRepositoryProtocol
    from lapidarium.pacts.db import TransactionProtocol
    from lapidarium.pacts.feeds import (
        ExternalItemRepositoryProtocol,
        FeedSourceProtocol,
    )


def same_page(url: str) -> str:
    """Reduce `url` to what names the page: no scheme, `www.`, slash or param order."""
    parts = urlsplit(url)
    host = (parts.hostname or "").removeprefix("www.").removeprefix("m.")
    path = parts.path.rstrip("/")
    return f"{host}{path}?{urlencode(sorted(parse_qsl(parts.query)))}"


def _copy_key(url: str) -> str:
    """Name what `url` shows: a YouTube video by its id, else the page."""
    return f"youtube:{video}" if (video := youtube_id(url)) else same_page(url)


class FeedSyncService(FeedSyncServiceProtocol):
    def __init__(
        self,
        *,
        sources: Sequence[FeedSourceProtocol],
        external: ExternalItemRepositoryProtocol,
        entries: EntryRepositoryProtocol,
        transaction: TransactionProtocol,
    ) -> None:
        self._sources = sources
        self._external = external
        self._entries = entries
        self._transaction = transaction

    @override
    def sync(self) -> FeedSyncDTO:
        copies = {
            _copy_key(link.url): EntryKeyDTO(type_key=entry.type_key, slug=entry.slug)
            for entry in self._entries.list_published()
            for link in entry.syndication
        }
        fetched = created = linked = 0
        failed: list[str] = []
        for source in self._sources:
            try:
                items = source.fetch()
            except FeedError:
                failed.append(source.name)
                continue
            with self._transaction.atomic():
                for item in items:
                    entry = copies.get(_copy_key(item["url"]))
                    created += self._external.save(item, entry=entry)
                    linked += entry is not None
            fetched += len(items)
        return FeedSyncDTO(
            fetched=fetched, created=created, linked=linked, failed=tuple(failed)
        )
