"""What frames every public page, and the page about the person behind it."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from lapidarium.mills.catalogue import Catalogue, newest_first
from lapidarium.mills.schema import mix
from lapidarium.pacts import CONTAINER_ROLES, AboutDTO, SiteDTO, SiteServiceProtocol
from lapidarium.specs import TINT_MIX

if TYPE_CHECKING:
    from lapidarium.pacts import (
        EntryRepositoryProtocol,
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
        entries: EntryRepositoryProtocol,
        profile: ProfileRepositoryProtocol,
        theme: ThemeServiceProtocol,
    ) -> None:
        self._schema = schema
        self._theme = theme
        self._types = types
        self._entries = entries
        self._profile = profile

    @override
    def chrome(self) -> SiteDTO:
        types = self._types.list_all()
        # Keys are slugs and colours are #rrggbb, both checked on save.
        type_css = "\n".join(
            f'[data-type="{t.key}"] {{ --type-color: {t.colour};'
            f" --type-tint: {t.tint or self._schema.derive_tint(t.colour)}; }}"
            for t in types
        )
        if dark := self._theme.dark_background():
            rules = "\n".join(
                f'  [data-type="{t.key}"] {{ --type-tint:'
                f" {mix(t.colour, dark, share=TINT_MIX)}; }}"
                for t in types
            )
            type_css += f"\n@media (prefers-color-scheme: dark) {{\n{rules}\n}}"
        return SiteDTO(
            profile=self._profile.get(),
            links=tuple(self._profile.list_links()),
            types=tuple(types),
            menu=tuple(t for t in types if t.in_menu),
            type_css=type_css,
            theme=self._theme.active(),
        )

    @override
    def about(self) -> AboutDTO:
        catalogue = Catalogue(self._types.list_all(), self._entries.list_published())
        containers = [
            e
            for e in catalogue.entries
            if catalogue.types[e.type_key].role in CONTAINER_ROLES
        ]
        return AboutDTO(
            profile=self._profile.get(),
            links=tuple(self._profile.list_links()),
            timeline=catalogue.cards(newest_first(containers)),
        )
