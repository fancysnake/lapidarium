"""Who the site is about: profile, links, friends, the page chrome."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypedDict

from pydantic import BaseModel, ConfigDict

from lapidarium.pacts.content import EntryTypeDTO, MediaAssetDTO

if TYPE_CHECKING:
    from collections.abc import Sequence


# Width and height of a web button, the old-web badge one site links another with.
BUTTON_SIZE = (88, 31)


class ProfileData(TypedDict):
    name: str
    handle: str
    tagline: str
    photo: str
    bio: str
    email: str
    button: str
    friends_title: str
    friends_intro: str


class LinkData(TypedDict):
    platform: str
    url: str
    label: str


class FriendData(TypedDict):
    name: str
    url: str
    button: str


class ProfileDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    handle: str
    tagline: str
    photo: MediaAssetDTO | None
    bio: str
    email: str
    button: MediaAssetDTO | None
    friends_title: str
    friends_intro: str


class LinkDTO(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    platform: str
    url: str
    label: str


class FriendDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    url: str
    button: MediaAssetDTO | None


class TypeColourDTO(BaseModel):
    """A colour a scheme sets for one type."""

    model_config = ConfigDict(frozen=True)

    key: str
    colour: str


class SiteDTO(BaseModel):
    """What every public page shows around its content."""

    model_config = ConfigDict(frozen=True)

    profile: ProfileDTO | None
    # The profile's name, or the site name when the profile has none.
    owner_name: str
    links: tuple[LinkDTO, ...]
    types: tuple[EntryTypeDTO, ...]
    menu: tuple[EntryTypeDTO, ...]
    dark_colours: tuple[TypeColourDTO, ...]


class ProfileRepositoryProtocol(Protocol):
    def get(self) -> ProfileDTO | None: ...

    def list_links(self) -> list[LinkDTO]: ...

    def save(self, data: ProfileData) -> None: ...

    def replace_links(self, links: Sequence[LinkData]) -> None: ...

    def list_friends(self) -> list[FriendDTO]: ...

    def replace_friends(self, friends: Sequence[FriendData]) -> None: ...
