"""Items from feeds elsewhere, and the sources that list them."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Protocol, TypedDict

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from lapidarium.pacts.content import EntryKeyDTO


class FeedError(Exception):
    pass


class ExternalItemData(TypedDict):
    source: str
    external_id: str
    title: str
    url: str
    published_at: dt.datetime
    thumbnail_url: str


class ExternalItemDTO(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    source: str
    title: str
    url: str
    published_at: dt.datetime


class FeedSyncDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    fetched: int
    created: int
    linked: int
    failed: tuple[str, ...]


class ExternalItemRepositoryProtocol(Protocol):
    def list_recent(self, limit: int) -> list[ExternalItemDTO]:
        """Newest first, unless linked to an entry, which speaks for them."""

    def save(self, item: ExternalItemData, *, entry: EntryKeyDTO | None) -> bool:
        """Create or update by source and external id; True when created."""


class FeedSourceProtocol(Protocol):
    @property
    def name(self) -> str: ...

    def fetch(self) -> list[ExternalItemData]:
        """Items the feed lists now; `FeedError` when it cannot be read."""
