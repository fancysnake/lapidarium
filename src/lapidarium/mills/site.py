"""What frames every public page."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from lapidarium.pacts.services import SiteServiceProtocol
from lapidarium.pacts.site import SiteDTO

if TYPE_CHECKING:
    from lapidarium.pacts.content import ProfileRepositoryProtocol
    from lapidarium.pacts.schema import EntryTypeRepositoryProtocol


class SiteService(SiteServiceProtocol):
    def __init__(
        self,
        *,
        types: EntryTypeRepositoryProtocol,
        profile: ProfileRepositoryProtocol,
        site_name: str,
    ) -> None:
        self._types = types
        self._profile = profile
        self._site_name = site_name

    @override
    def chrome(self) -> SiteDTO:
        types = tuple(self._types.list_all())
        profile = self._profile.get()
        return SiteDTO(
            profile=profile,
            owner_name=(profile.name if profile else "") or self._site_name,
            links=tuple(self._profile.list_links()),
            types=types,
            menu=tuple(t for t in types if t.in_menu),
        )
