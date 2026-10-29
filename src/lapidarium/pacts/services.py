"""Service protocols, and the namespace gates reach them through."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
    from pathlib import Path

    from lapidarium.pacts.catalogue import (
        CardDTO,
        DetailDTO,
        FeedItemDTO,
        HomeDTO,
        ListingDTO,
    )
    from lapidarium.pacts.content import (
        ContentSummaryDTO,
        EntryTypeDTO,
        LocalSetupDTO,
        Metadata,
        MetadataInput,
        PartData,
        PartKind,
        RelationEndDTO,
        TypeRole,
    )
    from lapidarium.pacts.maintenance import MaintenanceNoticeDTO
    from lapidarium.pacts.outreach import ContactData
    from lapidarium.pacts.site import FriendDTO, SiteDTO
    from lapidarium.pacts.theme import ProblemDTO, SiteThemeDTO


class SchemaServiceProtocol(Protocol):
    def validate_metadata(
        self, entry_type: EntryTypeDTO, values: Mapping[str, MetadataInput]
    ) -> Metadata:
        """Return cleaned metadata, or raise `MetadataValidationError`."""

    def check_builtins(
        self, role: TypeRole, values: Mapping[str, object]
    ) -> dict[str, str]:
        """Per-column errors for built-ins the role requires or does not use."""

    def check_part(self, part: PartData, asset_alt: str | None) -> list[str]:
        """Errors for one part; `asset_alt` is `None` when no asset is attached."""

    def check_part_kinds(
        self, entry_type: EntryTypeDTO, kinds: Sequence[PartKind]
    ) -> list[str]: ...

    def check_relation(
        self, role: str, *, source: RelationEndDTO, target: RelationEndDTO
    ) -> list[str]:
        """Errors for one link from `source` to `target`; loops are `check_loop`'s."""

    def check_loop[K: Hashable](
        self,
        role: str,
        *,
        entry: K,
        target: K,
        containers: Callable[[set[K]], Iterable[K]],
    ) -> list[str]:
        """Errors when linking `entry` to `target` as `role` closes a `part_of` loop.

        `containers` maps a set of entries to every entry they are `part_of`.
        """

    def check_relation_roles(
        self, entry_type: EntryTypeDTO, roles: Iterable[str]
    ) -> list[str]:
        """Errors for the type's required relation fields `roles` leaves unlinked."""

    def derive_tint(self, colour: str) -> str:
        """Mix `colour` over the page background."""

    def check_colours(self, colour: str, tint: str) -> list[str]:
        """Contrast errors for a type colour against the background and its tint."""

    def derive_dark_colour(self, colour: str) -> str | None:
        """Lighten `colour` to read in the dark scheme; `None` without one."""


class ContentExportServiceProtocol(Protocol):
    def export(self, root: Path) -> ContentSummaryDTO: ...


class ContentImportServiceProtocol(Protocol):
    def import_from(self, root: Path) -> ContentSummaryDTO: ...

    def demo_names(self) -> tuple[str, ...]: ...

    def load_demo(self, name: str) -> ContentSummaryDTO: ...


class LocalSetupServiceProtocol(Protocol):
    def set_up(self, demo: str, *, username: str, password: str) -> LocalSetupDTO: ...


class SiteServiceProtocol(Protocol):
    def chrome(self) -> SiteDTO: ...

    def friends(self) -> tuple[FriendDTO, ...]: ...


class MaintenanceServiceProtocol(Protocol):
    def notice(self) -> MaintenanceNoticeDTO | None:
        """Return what visitors see instead of the site; `None` while it is live."""


class CatalogueServiceProtocol(Protocol):
    def home(self) -> HomeDTO: ...

    def listing(
        self, route: str, *, filters: Mapping[str, str], page: int
    ) -> ListingDTO:
        """`NotFoundError` for an unknown route or a page past the last."""

    def detail(self, route: str, slug: str) -> DetailDTO:
        """`NotFoundError` unless published, on a type with detail pages."""

    def whats_new(self) -> tuple[FeedItemDTO, ...]: ...

    def search(self, query: str) -> tuple[CardDTO, ...]: ...

    def timeline(self) -> tuple[CardDTO, ...]:
        """Container entries, newest first."""

    def upcoming(self) -> tuple[CardDTO, ...]:
        """Calendar entries not yet over, soonest first."""


class OutreachServiceProtocol(Protocol):
    def can_contact(self) -> bool:
        """Whether the profile has an address for the contact form to reach."""

    def subscribe(self, email: str, *, sender: str) -> None:
        """`RateLimitedError` or `DeliveryError`."""

    def contact(self, message: ContactData, *, sender: str) -> None:
        """Mail the profile; `NotFoundError` without an address to mail to."""


class ThemeServiceProtocol(Protocol):
    def active(self) -> SiteThemeDTO: ...

    def check(self) -> list[ProblemDTO]:
        """Return what is wrong with the active theme, errors first."""

    def background(self) -> str:
        """Return the page background type colours must stand out against."""

    def dark_background(self) -> str | None:
        """Return the dark-scheme page background; `None` without dark tokens."""


class ServicesProtocol(Protocol):
    """The flat service namespace a gate reaches as `request.services`."""

    @property
    def schema(self) -> SchemaServiceProtocol: ...

    @property
    def content_export(self) -> ContentExportServiceProtocol: ...

    @property
    def content_import(self) -> ContentImportServiceProtocol: ...

    @property
    def local_setup(self) -> LocalSetupServiceProtocol: ...

    @property
    def site(self) -> SiteServiceProtocol: ...

    @property
    def maintenance(self) -> MaintenanceServiceProtocol: ...

    @property
    def catalogue(self) -> CatalogueServiceProtocol: ...

    @property
    def outreach(self) -> OutreachServiceProtocol: ...

    @property
    def theme(self) -> ThemeServiceProtocol: ...


class RootRequestProtocol(Protocol):
    """The slice of the framework request the middleware touches."""

    services: ServicesProtocol
