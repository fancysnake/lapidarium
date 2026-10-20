"""Entries, media, the profile, and the export bundle they travel in."""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, TypedDict

from pydantic import BaseModel, ConfigDict

from lapidarium.pacts.schema import EntryTypeDTO, Metadata, PartKind

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from lapidarium.pacts.schema import EntryTypeData


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


SUMMARY_MAX_LENGTH = 200
EXPORT_FORMAT_VERSION = 1


class NotFoundError(Exception):
    pass


class BundleValidationError(Exception):
    """An export bundle that breaks the content rules, messages grouped by file."""

    def __init__(self, errors: Mapping[str, Sequence[str]]) -> None:
        super().__init__(
            "\n".join(
                f"{where}: {msg}" for where, msgs in errors.items() for msg in msgs
            )
        )
        self.errors = {where: list(msgs) for where, msgs in errors.items()}


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


class ExportDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: ContentSummaryDTO
    committed: bool


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


class MediaAssetRepositoryProtocol(Protocol):
    def read(self, path: str) -> bytes: ...

    def save(self, data: AssetData) -> MediaAssetDTO:
        """Create or update the row by path; the file is left to `write`."""

    def write(self, path: str, *, content: bytes) -> None:
        """Store `content` under exactly `path`, replacing any file there."""


class ProfileRepositoryProtocol(Protocol):
    def get(self) -> ProfileDTO | None: ...

    def list_links(self) -> list[LinkDTO]: ...

    def save(self, data: ProfileData) -> None: ...

    def replace_links(self, links: Sequence[LinkData]) -> None: ...


class ArchiveProtocol(Protocol):
    """A version-controlled directory the export is written into."""

    def commit(self, root: Path, *, message: str) -> bool:
        """Record every change under `root`; False when there was none."""

    def push(self, root: Path) -> None:
        """Send commits to the default remote; `DeliveryError` when refused."""


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
