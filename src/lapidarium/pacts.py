"""Contracts crossing layer boundaries: DTOs, protocols, enums, errors."""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, TypedDict

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from contextlib import AbstractContextManager
    from pathlib import Path

# Enums


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
SUMMARY_MAX_LENGTH = 200
EXPORT_FORMAT_VERSION = 1

type MetadataValue = str | int | float | bool
type Metadata = dict[str, MetadataValue]
type MetadataInput = str | int | float | bool | dt.date | None


# Errors


class NotFoundError(Exception):
    pass


class MetadataValidationError(Exception):
    """Metadata that does not fit its type's schema, one message per field key."""

    def __init__(self, errors: Mapping[str, str]) -> None:
        super().__init__("; ".join(f"{key}: {msg}" for key, msg in errors.items()))
        self.errors = dict(errors)


class BundleValidationError(Exception):
    """An export bundle that cannot be imported, messages grouped by file."""

    def __init__(self, errors: Mapping[str, Sequence[str]]) -> None:
        super().__init__(
            "\n".join(
                f"{where}: {msg}" for where, msgs in errors.items() for msg in msgs
            )
        )
        self.errors = {where: list(msgs) for where, msgs in errors.items()}


# Write shapes: what gates and the content store hand to mills, and mills to links.


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


class ProfileData(TypedDict):
    name: str
    handle: str
    tagline: str
    photo: str
    bio: str
    email: str


class LinkData(TypedDict):
    platform: str
    url: str
    label: str


class ContentBundle(TypedDict):
    """Everything export format v1 holds, as one value."""

    profile: ProfileData | None
    links: list[LinkData]
    types: list[EntryTypeData]
    entries: list[EntryData]
    assets: list[AssetData]


# DTOs


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
    order: int


class EntryTypeDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    pk: int
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

    pk: int
    path: str
    url: str
    alt: str


class PartDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: PartKind
    order: int
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
    order: int
    target: EntryRefDTO


class SyndicationLinkDTO(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    platform: str
    url: str


class EntryDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    pk: int
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


class ProfileDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    handle: str
    tagline: str
    photo: MediaAssetDTO | None
    bio: str
    email: str


class LinkDTO(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    platform: str
    url: str
    label: str
    order: int


class ContentSummaryDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    types: int
    entries: int
    assets: int


# Repository and port protocols


class TransactionProtocol(Protocol):
    def atomic(self) -> AbstractContextManager[None]: ...


class EntryTypeRepositoryProtocol(Protocol):
    def list_all(self) -> list[EntryTypeDTO]: ...

    def save_all(self, types: Sequence[EntryTypeData]) -> None:
        """Create or update each by key; field lists are replaced."""


class EntryRepositoryProtocol(Protocol):
    def list_published(self) -> list[EntryDTO]: ...

    def save(self, data: EntryData) -> None:
        """Create or update by type and slug; relations are left alone."""

    def set_relations(
        self, type_key: str, slug: str, *, relations: Sequence[RelationData]
    ) -> None:
        """Replace an entry's outgoing relations; `NotFoundError` on a missing end."""


class MediaAssetRepositoryProtocol(Protocol):
    def read(self, path: str) -> bytes: ...

    def save(self, data: AssetData) -> MediaAssetDTO:
        """Create or update by path."""


class ProfileRepositoryProtocol(Protocol):
    def get(self) -> ProfileDTO | None: ...

    def list_links(self) -> list[LinkDTO]: ...

    def save(self, data: ProfileData) -> None: ...

    def replace_links(self, links: Sequence[LinkData]) -> None: ...


class ContentStoreProtocol(Protocol):
    """Export format v1 on disk: `types/`, `content/`, `assets/`."""

    def read(self, root: Path) -> ContentBundle: ...

    def write(self, root: Path, bundle: ContentBundle) -> None: ...

    def demo_names(self) -> tuple[str, ...]: ...

    def read_demo(self, name: str) -> ContentBundle:
        """Bundled fixture set; `NotFoundError` for an unknown name."""


# Service protocols


class SchemaServiceProtocol(Protocol):
    def check_url(self, url: str, url_kind: UrlKind) -> str | None:
        """Error message, or `None` when the URL fits the kind."""

    def validate_metadata(
        self, entry_type: EntryTypeDTO, values: Mapping[str, MetadataInput]
    ) -> Metadata:
        """Return cleaned metadata, or raise `MetadataValidationError`."""

    def check_builtins(self, role: TypeRole, values: BuiltinValues) -> dict[str, str]:
        """Per-column errors for built-ins the role requires or does not use."""

    def check_part(self, part: PartData, asset_alt: str | None) -> list[str]:
        """Errors for one part; `asset_alt` is `None` when no asset is attached."""

    def check_part_kinds(
        self, entry_type: EntryTypeDTO, kinds: Sequence[PartKind]
    ) -> list[str]: ...

    def derive_tint(self, colour: str) -> str: ...

    def check_colours(self, colour: str, tint: str) -> list[str]:
        """Contrast errors for a type colour against the background and its tint."""


class ContentExportServiceProtocol(Protocol):
    def export(self, root: Path) -> ContentSummaryDTO: ...


class ContentImportServiceProtocol(Protocol):
    def import_from(self, root: Path) -> ContentSummaryDTO: ...

    def demo_names(self) -> tuple[str, ...]: ...

    def load_demo(self, name: str) -> ContentSummaryDTO: ...


class ServicesProtocol(Protocol):
    """The flat service namespace a gate reaches as `request.services`."""

    @property
    def schema(self) -> SchemaServiceProtocol: ...

    @property
    def content_export(self) -> ContentExportServiceProtocol: ...

    @property
    def content_import(self) -> ContentImportServiceProtocol: ...


class RootRequestProtocol(Protocol):
    """The slice of the framework request the middleware touches."""

    services: ServicesProtocol
