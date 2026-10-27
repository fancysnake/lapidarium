"""What frames every public page."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from lapidarium.pacts import SiteDTO, SiteServiceProtocol, TypeColourDTO

if TYPE_CHECKING:
    from lapidarium.pacts import (
        EntryTypeRepositoryProtocol,
        ProfileRepositoryProtocol,
        SchemaServiceProtocol,
    )


class SiteService(SiteServiceProtocol):
    def __init__(
        self,
        *,
        types: EntryTypeRepositoryProtocol,
        profile: ProfileRepositoryProtocol,
        schema: SchemaServiceProtocol,
        site_name: str,
    ) -> None:
        self._types = types
        self._profile = profile
        self._schema = schema
        self._site_name = site_name

    @override
    def chrome(self) -> SiteDTO:
        types = tuple(self._types.list_all())
        profile = self._profile.get()
        return SiteDTO(
            profile=profile,
            owner_name=(profile.name if profile else "") or self._site_name,
            links=tuple(self._profile.list_links()),
            friends=tuple(self._profile.list_friends()),
            types=types,
            menu=tuple(t for t in types if t.in_menu),
            dark_colours=tuple(
                TypeColourDTO(key=t.key, colour=dark)
                for t in types
                if (dark := self._schema.derive_dark_colour(t.colour))
                not in {None, t.colour}
            ),
        )
