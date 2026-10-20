"""Items published elsewhere, pulled in and tied to the entries they copy."""

from __future__ import annotations

from typing import TYPE_CHECKING, override
from urllib.parse import parse_qsl, urlencode, urlsplit

from lapidarium.pacts.feeds import FeedSyncDTO
from lapidarium.pacts.outreach import DeliveryError
from lapidarium.pacts.services import FeedSyncServiceProtocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lapidarium.pacts.content import EntryRepositoryProtocol
    from lapidarium.pacts.db import TransactionProtocol
    from lapidarium.pacts.feeds import (
        ExternalItemRepositoryProtocol,
        FeedSourceProtocol,
    )

_SHORT_HOSTS = {"youtu.be": "youtube.com/watch"}


def same_page(url: str) -> str:
    """Reduce `url` to what names the page: no scheme, `www.`, slash or param order."""
    parts = urlsplit(url)
    host = (parts.hostname or "").removeprefix("www.").removeprefix("m.")
    path = parts.path.rstrip("/")
    query = sorted(parse_qsl(parts.query))
    if host in _SHORT_HOSTS:
        query = sorted([*query, ("v", path.strip("/"))])
        host, path = _SHORT_HOSTS[host].split("/", 1)[0], "/watch"
    return f"{host}{path}?{urlencode(query)}"


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
            same_page(link.url): (entry.type_key, entry.slug)
            for entry in self._entries.list_published()
            for link in entry.syndication
        }
        fetched = created = linked = 0
        failed: list[str] = []
        for source in self._sources:
            try:
                items = source.fetch()
            except DeliveryError:
                failed.append(source.name)
                continue
            with self._transaction.atomic():
                for item in items:
                    entry = copies.get(same_page(item["url"]))
                    created += self._external.save(item, entry=entry)
                    linked += entry is not None
            fetched += len(items)
        return FeedSyncDTO(
            fetched=fetched, created=created, linked=linked, failed=tuple(failed)
        )
