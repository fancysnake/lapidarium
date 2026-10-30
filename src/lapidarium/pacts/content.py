"""Content: types, fields, entries, assets and the export bundle."""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, TypedDict

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from lapidarium.pacts.site import FriendData, LinkData, ProfileData


class TypeRole(StrEnum):
    THING = "thing"
    CONTAINER_OUTCOME = "container_outcome"
    CONTAINER_TIMESPAN = "container_timespan"
    CALENDAR = "calendar"
    SECTION = "section"


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


class EntryStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class Outcome(StrEnum):
    ONGOING = "ongoing"
    FINISHED = "finished"
    ABANDONED = "abandoned"


class RelationRole(StrEnum):
    """Built-in roles; schema-defined roles are the keys of `relation` fields."""

    PART_OF = "part_of"
    RELATED = "related"


class ListFilter(StrEnum):
    """Built-in list filters; the others are keys of the type's fields."""

    YEAR = "year"
    TAG = "tag"


# Which role-dependent built-ins a type's entries carry, and which they must fill.
# Columns outside this map (title, summary, status, cover, tags…) apply to every role.
ROLE_BUILTINS: Mapping[TypeRole, frozenset[str]] = {
    TypeRole.THING: frozenset({"date"}),
    TypeRole.CALENDAR: frozenset({"start_at", "end_at", "location", "is_online"}),
    TypeRole.CONTAINER_TIMESPAN: frozenset({"start_at", "end_at"}),
    TypeRole.CONTAINER_OUTCOME: frozenset({"outcome", "start_at", "end_at"}),
    TypeRole.SECTION: frozenset(),
}


ROLE_REQUIRED: Mapping[TypeRole, frozenset[str]] = {
    TypeRole.THING: frozenset(),
    TypeRole.CALENDAR: frozenset({"start_at"}),
    TypeRole.CONTAINER_TIMESPAN: frozenset({"start_at"}),
    TypeRole.CONTAINER_OUTCOME: frozenset({"outcome"}),
    TypeRole.SECTION: frozenset(),
}


CONTAINER_ROLES = frozenset(
    {TypeRole.CONTAINER_OUTCOME, TypeRole.CONTAINER_TIMESPAN, TypeRole.SECTION}
)


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


SUMMARY_MAX_LENGTH = 200


EXPORT_FORMAT_VERSION = 1


# Cache alias for rendered public pages; every content commit clears it.
PAGE_CACHE = "pages"


type MetadataValue = str | int | float | bool


type Metadata = dict[str, MetadataValue]


type MetadataInput = str | int | float | bool | dt.date | None


class NotFoundError(Exception):
    pass


class MetadataValidationError(Exception):
    """Metadata that does not fit its type's schema, one message per field key."""

    def __init__(self, errors: Mapping[str, str]) -> None:
        super().__init__("; ".join(f"{key}: {msg}" for key, msg in errors.items()))
        self.errors = dict(errors)


class BundleValidationError(Exception):
    """An export bundle that breaks the content rules, messages grouped by file."""

    def __init__(self, errors: Mapping[str, Sequence[str]]) -> None:
        super().__init__(
            "\n".join(
                f"{where}: {msg}" for where, msgs in errors.items() for msg in msgs
            )
        )
        self.errors = {where: list(msgs) for where, msgs in errors.items()}


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


class PartData(TypedDict):
    kind: PartKind
    text: str
    url: str
    asset: str
    caption: str
    options: dict[str, str]


class RelationData(TypedDict):
    role: str
    target_type: str
    target_slug: str


class SyndicationData(TypedDict):
    platform: str
    url: str


class BuiltinValues(TypedDict):
    date: dt.date | None
    start_at: dt.datetime | None
    end_at: dt.datetime | None
    location: str
    is_online: bool
    outcome: str


# Role-dependent built-ins left empty, in form order.
BUILTIN_DEFAULTS: Mapping[str, str | bool | None] = {
    "date": None,
    "start_at": None,
    "end_at": None,
    "location": "",
    "is_online": False,
    "outcome": "",
}


class EntryData(BuiltinValues):
    type: str
    slug: str
    title: str
    summary: str
    external_url: str
    status: EntryStatus
    featured: bool
    hide_from_whats_new: bool
    license: str
    cover: str
    tags: list[str]
    metadata: Metadata
    parts: list[PartData]
    relations: list[RelationData]
    syndication: list[SyndicationData]
    created_at: dt.datetime | None
    updated_at: dt.datetime | None


class AssetData(TypedDict):
    path: str
    alt: str
    content: bytes


class ShowcaseItemData(TypedDict):
    type: str
    slug: str


class ShowcaseData(TypedDict):
    title: str
    intro: str
    hidden: bool
    entries: list[ShowcaseItemData]


class ContentBundle(TypedDict):
    """Everything export format v1 holds, as one value."""

    profile: ProfileData | None
    links: list[LinkData]
    friends: list[FriendData]
    showcases: list[ShowcaseData]
    types: list[EntryTypeData]
    entries: list[EntryData]
    assets: list[AssetData]


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


class MediaAssetDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    url: str
    alt: str


class PartDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: PartKind
    text: str
    url: str
    asset: MediaAssetDTO | None
    caption: str
    options: dict[str, str]


class EntryRefDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    type_key: str
    slug: str
    title: str
    status: EntryStatus


class RelationDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: str
    target: EntryRefDTO


class SyndicationLinkDTO(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    platform: str
    url: str


class EntryDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    type_key: str
    slug: str
    title: str
    summary: str
    date: dt.date | None
    start_at: dt.datetime | None
    end_at: dt.datetime | None
    location: str
    is_online: bool
    external_url: str
    status: EntryStatus
    featured: bool
    hide_from_whats_new: bool
    license: str
    outcome: str
    cover: MediaAssetDTO | None
    tags: tuple[str, ...]
    metadata: Metadata
    parts: tuple[PartDTO, ...]
    relations: tuple[RelationDTO, ...]
    syndication: tuple[SyndicationLinkDTO, ...]
    created_at: dt.datetime
    updated_at: dt.datetime


class ShowcaseDTO(BaseModel):
    """Entries the owner picked by hand, in order, drafts among them."""

    model_config = ConfigDict(frozen=True)

    title: str
    intro: str
    hidden: bool
    entries: tuple[EntryRefDTO, ...]


class RelationEndDTO(BaseModel):
    """One end of a link between entries, as the relation rules see it."""

    model_config = ConfigDict(frozen=True)

    entry_type: EntryTypeDTO
    status: EntryStatus


class ContentSummaryDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    types: int
    entries: int
    assets: int


class LocalSetupDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: ContentSummaryDTO
    superuser_created: bool


class EntryTypeRepositoryProtocol(Protocol):
    def list_all(self) -> list[EntryTypeDTO]: ...

    def save_all(self, types: Sequence[EntryTypeData]) -> None:
        """Create or update each by key; field lists are replaced."""


class EntryRepositoryProtocol(Protocol):
    def list_published(self) -> list[EntryDTO]: ...

    def search(self, terms: Sequence[str], *, limit: int) -> list[EntryDTO]:
        """Return up to `limit` published entries holding every term, ignoring case."""

    def save(self, data: EntryData) -> None:
        """Create or update by type and slug; relations are left alone."""

    def set_relations(
        self, type_key: str, slug: str, *, relations: Sequence[RelationData]
    ) -> None:
        """Replace an entry's outgoing relations; `NotFoundError` on a missing end."""

    def list_showcases(self) -> list[ShowcaseDTO]: ...

    def replace_showcases(self, showcases: Sequence[ShowcaseData]) -> None:
        """Replace every showcase; `NotFoundError` on an entry that does not exist."""


class MediaAssetRepositoryProtocol(Protocol):
    def read(self, path: str) -> bytes: ...

    def save(self, data: AssetData) -> MediaAssetDTO:
        """Create or update the row by path; the file is left to `write`."""

    def write(self, path: str, *, content: bytes) -> None:
        """Store `content` under exactly `path`, replacing any file there."""


class AccountRepositoryProtocol(Protocol):
    def ensure_superuser(self, username: str, *, password: str) -> bool:
        """Create the superuser or reset it to `password`; True when created."""


class ContentStoreProtocol(Protocol):
    """Export format v1 on disk: `types/`, `content/`, `assets/`."""

    def read(self, root: Path) -> ContentBundle: ...

    def write(self, root: Path, bundle: ContentBundle) -> None: ...

    def demo_names(self) -> tuple[str, ...]: ...

    def read_demo(self, name: str) -> ContentBundle:
        """Bundled fixture set; `NotFoundError` for an unknown name."""
