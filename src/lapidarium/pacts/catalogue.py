"""The public catalogue: home, lists, detail pages, and what's new."""

from __future__ import annotations

import datetime as dt
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from lapidarium.pacts.content import EntryDTO, EntryRefDTO
from lapidarium.pacts.schema import EntryTypeDTO, FieldKind, MetadataValue


class FeedChange(StrEnum):
    ADDED = "added"
    UPDATED = "updated"
    EXTERNAL = "external"


class ListFilter(StrEnum):
    """Built-in list filters; the others are keys of the type's fields."""

    YEAR = "year"
    TAG = "tag"


class FactDTO(BaseModel):
    """One schema field of an entry, ready to show; relation fields carry `refs`."""

    model_config = ConfigDict(frozen=True)

    label: str
    kind: FieldKind
    value: MetadataValue | None
    refs: tuple[EntryRefDTO, ...]


class CardDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    entry: EntryDTO
    entry_type: EntryTypeDTO
    facts: tuple[FactDTO, ...]


class DoorDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    entry_type: EntryTypeDTO
    label: str
    pick: CardDTO


class FeedItemDTO(BaseModel):
    """A line of "what's new": an entry, or an item from a feed elsewhere."""

    model_config = ConfigDict(frozen=True)

    change: FeedChange
    when: dt.datetime
    title: str
    type_key: str
    type_label: str
    entry: EntryRefDTO | None
    url: str


class HomeDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    doors: tuple[DoorDTO, ...]
    whats_new: tuple[FeedItemDTO, ...]
    next_up: CardDTO | None


class FilterDTO(BaseModel):
    """A list filter; `label` is empty for the built-ins, which gates name."""

    model_config = ConfigDict(frozen=True)

    key: str
    label: str
    options: tuple[str, ...]
    selected: str


class ListingDTO(BaseModel):
    """One page of a type's list; calendar types also get every upcoming entry."""

    model_config = ConfigDict(frozen=True)

    entry_type: EntryTypeDTO
    filters: tuple[FilterDTO, ...]
    upcoming: tuple[CardDTO, ...]
    cards: tuple[CardDTO, ...]
    page: int
    pages: int
    total: int


class DetailDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    card: CardDTO
    panel: tuple[FactDTO, ...]
    containers: tuple[EntryRefDTO, ...]
    contents: tuple[CardDTO, ...]
    related: tuple[CardDTO, ...]
    siblings: tuple[CardDTO, ...]
    # Player address by video part URL; a URL with no known player is absent.
    embeds: dict[str, str]
