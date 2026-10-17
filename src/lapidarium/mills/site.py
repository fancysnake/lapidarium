"""What frames every public page."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from lapidarium.pacts import SiteDTO, SiteServiceProtocol

if TYPE_CHECKING:
    from lapidarium.pacts import (
        EntryTypeDTO,
        EntryTypeRepositoryProtocol,
        ProfileRepositoryProtocol,
        SchemaServiceProtocol,
        ThemeServiceProtocol,
    )


class SiteService(SiteServiceProtocol):
    def __init__(
        self,
        *,
        schema: SchemaServiceProtocol,
        types: EntryTypeRepositoryProtocol,
        profile: ProfileRepositoryProtocol,
        theme: ThemeServiceProtocol,
        site_name: str,
    ) -> None:
        self._schema = schema
        self._theme = theme
        self._types = types
        self._profile = profile
        self._site_name = site_name

    def _tinted(self, entry_type: EntryTypeDTO) -> EntryTypeDTO:
        if entry_type.tint:
            return entry_type
        tint = {"tint": self._schema.derive_tint(entry_type.colour)}
        return entry_type.model_copy(update=tint)

    def _dark_tinted(self, entry_type: EntryTypeDTO) -> EntryTypeDTO | None:
        if (dark_tint := self._schema.dark_tint(entry_type.colour)) is None:
            return None
        tint = {"tint": dark_tint}
        return entry_type.model_copy(update=tint)

    @override
    def chrome(self) -> SiteDTO:
        types = tuple(self._tinted(t) for t in self._types.list_all())
        dark = (self._dark_tinted(t) for t in types)
        dark_types = tuple(t for t in dark if t is not None)
        profile = self._profile.get()
        return SiteDTO(
            theme=self._theme.active(),
            profile=profile,
            owner_name=(profile.name if profile else "") or self._site_name,
            links=tuple(self._profile.list_links()),
            types=types,
            dark_types=dark_types,
            menu=tuple(t for t in types if t.in_menu),
        )
