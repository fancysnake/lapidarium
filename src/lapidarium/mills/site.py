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
    )


class SiteService(SiteServiceProtocol):
    def __init__(
        self,
        *,
        schema: SchemaServiceProtocol,
        types: EntryTypeRepositoryProtocol,
        profile: ProfileRepositoryProtocol,
    ) -> None:
        self._schema = schema
        self._types = types
        self._profile = profile

    def _tinted(self, entry_type: EntryTypeDTO) -> EntryTypeDTO:
        if entry_type.tint:
            return entry_type
        tint = {"tint": self._schema.derive_tint(entry_type.colour)}
        return entry_type.model_copy(update=tint)

    @override
    def chrome(self) -> SiteDTO:
        types = tuple(self._tinted(t) for t in self._types.list_all())
        return SiteDTO(
            profile=self._profile.get(),
            links=tuple(self._profile.list_links()),
            types=types,
            menu=tuple(t for t in types if t.in_menu),
        )
