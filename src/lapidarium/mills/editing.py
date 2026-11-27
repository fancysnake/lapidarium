"""The entries as the content panel lists them, drafts among them."""

from typing import TYPE_CHECKING, override

from lapidarium.mills.catalogue import page_of
from lapidarium.pacts.content import EntryStatus, NotFoundError, RelationRole
from lapidarium.pacts.editing import DeskDTO, EntryListDTO, EntryRowDTO, TypeCountDTO
from lapidarium.pacts.services import EditingServiceProtocol
from lapidarium.specs import DESK_RECENT, PANEL_PAGE_SIZE

if TYPE_CHECKING:
    from lapidarium.pacts.content import (
        EntryRepositoryProtocol,
        EntryTypeDTO,
        EntryTypeRepositoryProtocol,
    )


class EditingService(EditingServiceProtocol):
    def __init__(
        self, *, types: EntryTypeRepositoryProtocol, entries: EntryRepositoryProtocol
    ) -> None:
        self._types = types
        self._entries = entries

    def _rows(self, types: list[EntryTypeDTO]) -> list[EntryRowDTO]:
        by_key = {entry_type.key: entry_type for entry_type in types}
        return [
            EntryRowDTO(
                entry=entry,
                entry_type=by_key[entry.type_key],
                containers=tuple(
                    relation.target
                    for relation in entry.relations
                    if relation.role == RelationRole.PART_OF
                ),
            )
            for entry in self._entries.list_all()
        ]

    @override
    def desk(self) -> DeskDTO:
        rows = self._rows(self._types.list_all())
        published = [r for r in rows if r.entry.status == EntryStatus.PUBLISHED]
        return DeskDTO(
            drafts=tuple(r for r in rows if r.entry.status == EntryStatus.DRAFT),
            published=tuple(published[:DESK_RECENT]),
            total=len(rows),
        )

    def _matching(
        self, types: list[EntryTypeDTO], *, type_key: str, query: str
    ) -> tuple[EntryTypeDTO | None, list[EntryRowDTO]]:
        """Return the chosen type and its rows with `query` in the title."""
        entry_type = next((t for t in types if t.key == type_key), None)
        if type_key and entry_type is None:
            raise NotFoundError(type_key)
        rows = self._rows(types)
        if entry_type is not None:
            rows = [r for r in rows if r.entry_type.key == type_key]
        if needle := query.strip().casefold():
            rows = [r for r in rows if needle in r.entry.title.casefold()]
        return entry_type, rows

    @override
    def entries(
        self, *, type_key: str, status: EntryStatus | None, query: str, page: int
    ) -> EntryListDTO:
        types = self._types.list_all()
        entry_type, rows = self._matching(types, type_key=type_key, query=query)
        # The status buttons count every status, so the counts come first.
        published = sum(r.entry.status == EntryStatus.PUBLISHED for r in rows)
        total = len(rows)
        if status is not None:
            rows = [r for r in rows if r.entry.status == status]
        shown, pages = page_of(rows, page=page, size=PANEL_PAGE_SIZE, label="entries")
        counts = self._types.entry_counts()
        return EntryListDTO(
            rows=tuple(shown),
            types=tuple(
                TypeCountDTO(entry_type=t, entries=counts[t.key]) for t in types
            ),
            entry_type=entry_type,
            status=status,
            query=query.strip(),
            page=page,
            pages=pages,
            total=total,
            published=published,
            drafts=total - published,
        )
