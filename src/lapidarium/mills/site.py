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
    ) -> None:
        self._schema = schema
        self._theme = theme
        self._types = types
        self._profile = profile

    def _tinted(self, entry_type: EntryTypeDTO) -> EntryTypeDTO:
        if entry_type.tint:
            return entry_type
        tint = {"tint": self._schema.derive_tint(entry_type.colour)}
        return entry_type.model_copy(update=tint)

    def _dark_tinted(self, entry_type: EntryTypeDTO) -> EntryTypeDTO:
        tint = {"tint": self._schema.derive_tint(entry_type.colour, dark=True)}
        return entry_type.model_copy(update=tint)

    @override
    def chrome(self) -> SiteDTO:
        types = tuple(self._tinted(t) for t in self._types.list_all())
        dark_types: tuple[EntryTypeDTO, ...] = ()
        if self._theme.dark_background():
            dark_types = tuple(self._dark_tinted(t) for t in types)
        return SiteDTO(
            theme=self._theme.active(),
            profile=self._profile.get(),
            links=tuple(self._profile.list_links()),
            types=types,
            dark_types=dark_types,
            menu=tuple(t for t in types if t.in_menu),
        )
