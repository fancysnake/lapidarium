"""Entry types and their fields: roles, layouts, part kinds, metadata."""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, TypedDict

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


class TypeRole(StrEnum):
    THING = "thing"
    CONTAINER_OUTCOME = "container_outcome"
    CONTAINER_TIMESPAN = "container_timespan"
    CALENDAR = "calendar"


class Layout(StrEnum):
    ARTICLE = "article"
    MEDIA_FIRST = "media_first"
    GALLERY = "gallery"


class PartKind(StrEnum):
    TEXT = "text"
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    FILE = "file"
    LINK = "link"


class FieldKind(StrEnum):
    TEXT = "text"
    LONG_TEXT = "long_text"
    URL = "url"
    DATE = "date"
    NUMBER = "number"
    BOOL = "bool"
    CHOICE = "choice"
    RELATION = "relation"

    @property
    def can_be_missing(self) -> bool:
        """A switch left off is an answer, not a missing value."""
        return self is not FieldKind.BOOL


class UrlKind(StrEnum):
    ANY_HOST = "any"
    YOUTUBE = "youtube"
    ITCH = "itch"
    GITHUB = "github"


class DoorPick(StrEnum):
    LATEST_FEATURED = "latest_featured"
    LATEST = "latest"
    UPCOMING = "upcoming"
    RANDOM_FEATURED = "random_featured"


# Which role-dependent built-ins a type's entries carry, and which they must fill.
# Columns outside this map (title, summary, status, cover, tags…) apply to every role.
ROLE_BUILTINS: Mapping[TypeRole, frozenset[str]] = {
    TypeRole.THING: frozenset({"date"}),
    TypeRole.CALENDAR: frozenset({"start_at", "end_at", "location", "is_online"}),
    TypeRole.CONTAINER_TIMESPAN: frozenset({"start_at", "end_at"}),
    TypeRole.CONTAINER_OUTCOME: frozenset({"outcome", "start_at", "end_at"}),
}
ROLE_REQUIRED: Mapping[TypeRole, frozenset[str]] = {
    TypeRole.THING: frozenset(),
    TypeRole.CALENDAR: frozenset({"start_at"}),
    TypeRole.CONTAINER_TIMESPAN: frozenset({"start_at"}),
    TypeRole.CONTAINER_OUTCOME: frozenset({"outcome"}),
}
CONTAINER_ROLES = frozenset({TypeRole.CONTAINER_OUTCOME, TypeRole.CONTAINER_TIMESPAN})

# What a type or field setting is when left out, in the admin and in export files.
type SettingDefault = str | int | bool | tuple[str, ...]
DEFAULT_PARTS = (PartKind.TEXT,)
TYPE_DEFAULTS: Mapping[str, SettingDefault] = {
    "colour": "#000000",
    "tint": "",
    "icon": "",
    "order": 0,
    "in_menu": True,
    "role": TypeRole.THING,
    "layout": Layout.ARTICLE,
    "allowed_parts": DEFAULT_PARTS,
    "required_parts": (),
    "door_enabled": False,
    "door_label": "",
    "door_pick": DoorPick.LATEST_FEATURED,
    "door_min_entries": 1,
    "list_filters": (),
    "has_detail_page": True,
}
FIELD_DEFAULTS: Mapping[str, SettingDefault] = {
    "required": False,
    "choices": (),
    "url_kind": UrlKind.ANY_HOST,
    "target_type": "",
    "show_on_card": False,
    "show_in_metadata_panel": True,
}

type MetadataValue = str | int | float | bool
type Metadata = dict[str, MetadataValue]
type MetadataInput = str | int | float | bool | dt.date | None


class MetadataValidationError(Exception):
    """Metadata that does not fit its type's schema, one message per field key."""

    def __init__(self, errors: Mapping[str, str]) -> None:
        super().__init__("; ".join(f"{key}: {msg}" for key, msg in errors.items()))
        self.errors = dict(errors)


class FieldDefinitionData(TypedDict):
    key: str
    label: str
    kind: FieldKind
    required: bool
    choices: list[str]
    url_kind: UrlKind
    target_type: str
    show_on_card: bool
    show_in_metadata_panel: bool


class EntryTypeData(TypedDict):
    key: str
    label: str
    label_plural: str
    route: str
    colour: str
    tint: str
    icon: str
    order: int
    in_menu: bool
    role: TypeRole
    layout: Layout
    allowed_parts: list[PartKind]
    required_parts: list[PartKind]
    door_enabled: bool
    door_label: str
    door_pick: DoorPick
    door_min_entries: int
    list_filters: list[str]
    has_detail_page: bool
    fields: list[FieldDefinitionData]


class FieldDefinitionDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    label: str
    kind: FieldKind
    required: bool
    choices: tuple[str, ...]
    url_kind: UrlKind
    target_type: str
    show_on_card: bool
    show_in_metadata_panel: bool


class EntryTypeDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    label: str
    label_plural: str
    route: str
    colour: str
    tint: str
    icon: str
    order: int
    in_menu: bool
    role: TypeRole
    layout: Layout
    allowed_parts: tuple[PartKind, ...]
    required_parts: tuple[PartKind, ...]
    door_enabled: bool
    door_label: str
    door_pick: DoorPick
    door_min_entries: int
    list_filters: tuple[str, ...]
    has_detail_page: bool
    fields: tuple[FieldDefinitionDTO, ...]


class EntryTypeRepositoryProtocol(Protocol):
    def list_all(self) -> list[EntryTypeDTO]: ...

    def save_all(self, types: Sequence[EntryTypeData]) -> None:
        """Create or update each by key; field lists are replaced."""
