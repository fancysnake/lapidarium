"""What frames every public page."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from lapidarium.mills.schema import mix
from lapidarium.pacts import SiteDTO, SiteServiceProtocol
from lapidarium.specs import TINT_MIX

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

    @staticmethod
    def _dark_tinted(entry_type: EntryTypeDTO, dark: str) -> EntryTypeDTO:
        tint = {"tint": mix(entry_type.colour, dark, share=TINT_MIX)}
        return entry_type.model_copy(update=tint)

    @override
    def chrome(self) -> SiteDTO:
        types = tuple(self._tinted(t) for t in self._types.list_all())
        dark_types: tuple[EntryTypeDTO, ...] = ()
        if dark := self._theme.dark_background():
            dark_types = tuple(self._dark_tinted(t, dark) for t in types)
        return SiteDTO(
            theme=self._theme.active(),
            profile=self._profile.get(),
            links=tuple(self._profile.list_links()),
            types=types,
            dark_types=dark_types,
            menu=tuple(t for t in types if t.in_menu),
        )
