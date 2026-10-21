"""The public site: home, lists, details, what's new, search, calendar, timeline."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, override

from lapidarium.mills.video import video_embed
from lapidarium.pacts.catalogue import (
    CardDTO,
    DetailDTO,
    DoorDTO,
    FactDTO,
    FeedChange,
    FeedItemDTO,
    FilterDTO,
    HomeDTO,
    ListFilter,
    ListingDTO,
)
from lapidarium.pacts.content import EntryRefDTO, NotFoundError, RelationRole
from lapidarium.pacts.schema import (
    CONTAINER_ROLES,
    DoorPick,
    FieldKind,
    PartKind,
    TypeRole,
)
from lapidarium.pacts.services import CatalogueServiceProtocol
from lapidarium.specs import (
    PAGE_SIZE,
    SEARCH_LIMIT,
    SEARCH_MIN_LENGTH,
    SIBLINGS_LIMIT,
    UPDATE_GAP,
    WHATS_NEW_HOME,
    WHATS_NEW_PAGE,
)

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
    from random import Random

    from lapidarium.pacts.content import EntryDTO, EntryRepositoryProtocol
    from lapidarium.pacts.feeds import ExternalItemRepositoryProtocol
    from lapidarium.pacts.schema import (
        EntryTypeDTO,
        EntryTypeRepositoryProtocol,
        FieldDefinitionDTO,
    )

type _Key = tuple[str, str]
_BLANK = frozenset({None, ""})


def when(entry: EntryDTO) -> dt.date | None:
    """Return the day an entry happened, by whichever built-in its role uses."""
    if entry.date:
        return entry.date
    if entry.start_at:
        return entry.start_at.date()
    return None


def ends_at(entry: EntryDTO) -> dt.datetime | None:
    return entry.end_at or entry.start_at


def shows_door(entry_type: EntryTypeDTO, entries: Sequence[EntryDTO]) -> bool:
    """Return whether the home page shows a door to `entries`, all of this type."""
    return entry_type.door_enabled and len(entries) >= max(
        entry_type.door_min_entries, 1
    )


def _key(entry: EntryDTO) -> _Key:
    return entry.type_key, entry.slug


def entry_ref(entry: EntryDTO) -> EntryRefDTO:
    return EntryRefDTO(
        type_key=entry.type_key, slug=entry.slug, title=entry.title, status=entry.status
    )


def _age(entry: EntryDTO) -> tuple[dt.date, dt.datetime]:
    return when(entry) or entry.created_at.date(), entry.created_at


def _start(entry: EntryDTO) -> dt.datetime:
    return entry.start_at or entry.created_at


def _when(item: FeedItemDTO) -> dt.datetime:
    return item.when


def newest_first(entries: Iterable[EntryDTO]) -> list[EntryDTO]:
    return sorted(entries, key=_age, reverse=True)


def _filter_value(entry: EntryDTO, key: str) -> tuple[str, ...]:
    match key:
        case ListFilter.YEAR:
            day = when(entry)
            return (str(day.year),) if day else ()
        case ListFilter.TAG:
            return entry.tags
        case _:
            value = entry.metadata.get(key)
            return () if value in _BLANK else (str(value),)


class Catalogue:
    """Published entries of known types, indexed both ways along their relations."""

    def __init__(
        self, types: Sequence[EntryTypeDTO], entries: Sequence[EntryDTO]
    ) -> None:
        self.types = {t.key: t for t in types}
        self.entries = [e for e in entries if e.type_key in self.types]
        self._by_key = {_key(e): e for e in self.entries}
        self._backlinks: dict[_Key, list[tuple[str, EntryDTO]]] = {}
        for entry in self.entries:
            for relation in entry.relations:
                target = (relation.target.type_key, relation.target.slug)
                self._backlinks.setdefault(target, []).append((relation.role, entry))

    def get(self, type_key: str, slug: str) -> EntryDTO | None:
        return self._by_key.get((type_key, slug))

    def by_route(self, route: str) -> EntryTypeDTO:
        if (
            found := next((t for t in self.types.values() if t.route == route), None)
        ) is None:
            raise NotFoundError(route)
        return found

    def of_type(self, type_key: str) -> list[EntryDTO]:
        return [e for e in self.entries if e.type_key == type_key]

    def of_role(self, role: TypeRole) -> list[EntryDTO]:
        return [e for e in self.entries if self.types[e.type_key].role == role]

    def card(self, entry: EntryDTO) -> CardDTO:
        entry_type = self.types[entry.type_key]
        fields = [f for f in entry_type.fields if f.show_on_card]
        return CardDTO(
            entry=entry, entry_type=entry_type, facts=self.facts(entry, fields)
        )

    def cards(self, entries: Iterable[EntryDTO]) -> tuple[CardDTO, ...]:
        return tuple(self.card(entry) for entry in entries)

    def facts(
        self, entry: EntryDTO, fields: Iterable[FieldDefinitionDTO]
    ) -> tuple[FactDTO, ...]:
        facts: list[FactDTO] = []
        for field in fields:
            if field.kind == FieldKind.RELATION:
                if refs := self._targets(entry, field.key):
                    facts.append(
                        FactDTO(
                            label=field.label, kind=field.kind, value=None, refs=refs
                        )
                    )
                continue
            if (value := entry.metadata.get(field.key)) not in _BLANK:
                facts.append(
                    FactDTO(label=field.label, kind=field.kind, value=value, refs=())
                )
        return tuple(facts)

    def _outgoing(self, entry: EntryDTO) -> Iterator[tuple[str, EntryDTO]]:
        for relation in entry.relations:
            if target := self.get(relation.target.type_key, relation.target.slug):
                yield relation.role, target

    def linked(self, entry: EntryDTO, role: str) -> list[EntryDTO]:
        """Return the published entries `entry` links to as `role`."""
        return [target for r, target in self._outgoing(entry) if r == role]

    def neighbours(self, entry: EntryDTO) -> list[EntryDTO]:
        """Return the published entries linked to or from `entry`, in any role."""
        return [
            *(source for _, source in self._backlinks.get(_key(entry), [])),
            *(target for _, target in self._outgoing(entry)),
        ]

    def _targets(self, entry: EntryDTO, role: str) -> tuple[EntryRefDTO, ...]:
        return tuple(entry_ref(target) for target in self.linked(entry, role))

    def contents(self, entry: EntryDTO) -> list[EntryDTO]:
        """Return the entries that are part of `entry`."""
        return [
            source
            for role, source in self._backlinks.get(_key(entry), [])
            if role == RelationRole.PART_OF
        ]

    def backlinks(self, entry: EntryDTO) -> list[EntryDTO]:
        """Return the entries linking to `entry` as anything but part of it."""
        return [
            source
            for role, source in self._backlinks.get(_key(entry), [])
            if role != RelationRole.PART_OF
        ]


def _filters(
    entry_type: EntryTypeDTO, entries: Sequence[EntryDTO], *, chosen: Mapping[str, str]
) -> tuple[FilterDTO, ...]:
    """Return the type's list filters, each with the values its entries hold."""
    labels = {f.key: f.label for f in entry_type.fields}
    offered: list[FilterDTO] = []
    for key in entry_type.list_filters:
        if key not in ListFilter and key not in labels:
            continue
        options = sorted(
            {value for e in entries for value in _filter_value(e, key)},
            reverse=key == ListFilter.YEAR,
        )
        selected = chosen.get(key, "")
        offered.append(
            FilterDTO(
                key=key,
                label=labels.get(key, ""),
                options=tuple(options),
                selected=selected if selected in options else "",
            )
        )
    return tuple(offered)


def _unique(entries: Iterable[EntryDTO], *, besides: EntryDTO) -> list[EntryDTO]:
    seen = {_key(besides)}
    unique: list[EntryDTO] = []
    for entry in entries:
        if _key(entry) not in seen:
            seen.add(_key(entry))
            unique.append(entry)
    return unique


class CatalogueService(CatalogueServiceProtocol):
    def __init__(
        self,
        *,
        types: EntryTypeRepositoryProtocol,
        entries: EntryRepositoryProtocol,
        external: ExternalItemRepositoryProtocol,
        clock: Callable[[], dt.datetime],
        rng: Random,
    ) -> None:
        self._types = types
        self._entries = entries
        self._external = external
        self._clock = clock
        self._rng = rng

    def _catalogue(self) -> Catalogue:
        return Catalogue(self._types.list_all(), self._entries.list_published())

    def _upcoming(self, entries: Iterable[EntryDTO]) -> list[EntryDTO]:
        now = self._clock()
        ahead = [e for e in entries if (end := ends_at(e)) is not None and end >= now]
        return sorted(ahead, key=_start)

    @override
    def home(self) -> HomeDTO:
        catalogue = self._catalogue()
        doors: list[DoorDTO] = []
        for entry_type in catalogue.types.values():
            entries = catalogue.of_type(entry_type.key)
            if not shows_door(entry_type, entries):
                continue
            doors.append(
                DoorDTO(
                    entry_type=entry_type,
                    label=entry_type.door_label or entry_type.label_plural,
                    pick=catalogue.card(self._pick(entry_type.door_pick, entries)),
                )
            )
        upcoming = self._upcoming(catalogue.of_role(TypeRole.CALENDAR))
        return HomeDTO(
            doors=tuple(doors),
            whats_new=self._feed(catalogue, limit=WHATS_NEW_HOME),
            next_up=catalogue.card(upcoming[0]) if upcoming else None,
        )

    def _pick(self, pick: DoorPick, entries: Sequence[EntryDTO]) -> EntryDTO:
        newest = newest_first(entries)
        featured = [e for e in newest if e.featured]
        match pick:
            case DoorPick.LATEST_FEATURED:
                return (featured or newest)[0]
            case DoorPick.RANDOM_FEATURED:
                return self._rng.choice(featured or newest)
            case DoorPick.UPCOMING:
                return (self._upcoming(entries) or newest)[0]
            case _:
                return newest[0]

    @override
    def listing(
        self, route: str, *, filters: Mapping[str, str], page: int
    ) -> ListingDTO:
        catalogue = self._catalogue()
        entry_type = catalogue.by_route(route)
        entries = catalogue.of_type(entry_type.key)
        offered = _filters(entry_type, entries, chosen=filters)
        for chosen in offered:
            if chosen.selected:
                entries = [
                    e
                    for e in entries
                    if chosen.selected in _filter_value(e, chosen.key)
                ]
        upcoming: list[EntryDTO] = []
        if entry_type.role == TypeRole.CALENDAR:
            upcoming = self._upcoming(entries)
        shown_upcoming = {_key(e) for e in upcoming}
        rest = newest_first(e for e in entries if _key(e) not in shown_upcoming)
        pages = max(math.ceil(len(rest) / PAGE_SIZE), 1)
        if not 1 <= page <= pages:
            msg = f"{route} page {page}"
            raise NotFoundError(msg)
        shown = rest[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]
        return ListingDTO(
            entry_type=entry_type,
            filters=offered,
            upcoming=catalogue.cards(upcoming),
            cards=catalogue.cards(shown),
            page=page,
            pages=pages,
            total=len(entries),
        )

    @override
    def detail(self, route: str, slug: str) -> DetailDTO:
        catalogue = self._catalogue()
        entry_type = catalogue.by_route(route)
        entry = catalogue.get(entry_type.key, slug)
        if entry is None or not entry_type.has_detail_page:
            msg = f"{route}/{slug}"
            raise NotFoundError(msg)
        containers = catalogue.linked(entry, RelationRole.PART_OF)
        related = [
            *catalogue.linked(entry, RelationRole.RELATED),
            *catalogue.backlinks(entry),
        ]
        siblings = [
            sibling
            for container in containers
            for sibling in catalogue.contents(container)
        ]
        embeds = {
            part.url: embed
            for part in entry.parts
            if part.kind == PartKind.VIDEO and (embed := video_embed(part.url))
        }
        return DetailDTO(
            card=catalogue.card(entry),
            panel=catalogue.facts(
                entry, (f for f in entry_type.fields if f.show_in_metadata_panel)
            ),
            containers=tuple(entry_ref(container) for container in containers),
            contents=catalogue.cards(newest_first(catalogue.contents(entry))),
            related=catalogue.cards(_unique(related, besides=entry)),
            siblings=catalogue.cards(
                newest_first(_unique(siblings, besides=entry))[:SIBLINGS_LIMIT]
            ),
            embeds=embeds,
        )

    @override
    def whats_new(self) -> tuple[FeedItemDTO, ...]:
        return self._feed(self._catalogue(), limit=WHATS_NEW_PAGE)

    def _feed(self, catalogue: Catalogue, *, limit: int) -> tuple[FeedItemDTO, ...]:
        items = [
            FeedItemDTO(
                change=(
                    FeedChange.UPDATED
                    if entry.updated_at - entry.created_at > UPDATE_GAP
                    else FeedChange.ADDED
                ),
                when=entry.updated_at,
                title=entry.title,
                type_key=entry.type_key,
                type_label=catalogue.types[entry.type_key].label,
                entry=entry_ref(entry),
                url="",
            )
            for entry in catalogue.entries
            if not entry.hide_from_whats_new
        ]
        items.extend(
            FeedItemDTO(
                change=FeedChange.EXTERNAL,
                when=item.published_at,
                title=item.title,
                type_key=FeedChange.EXTERNAL,
                type_label=item.source,
                entry=None,
                url=item.url,
            )
            for item in self._external.list_recent(limit)
        )
        items.sort(key=_when, reverse=True)
        return tuple(items[:limit])

    @override
    def search(self, query: str) -> tuple[CardDTO, ...]:
        if len(query.strip()) < SEARCH_MIN_LENGTH:
            return ()
        found = self._entries.search(query.split(), limit=SEARCH_LIMIT)
        catalogue = self._catalogue()
        return catalogue.cards(
            entry for hit in found if (entry := catalogue.get(hit.type_key, hit.slug))
        )

    @override
    def timeline(self) -> tuple[CardDTO, ...]:
        catalogue = self._catalogue()
        containers = [
            e
            for e in catalogue.entries
            if catalogue.types[e.type_key].role in CONTAINER_ROLES
        ]
        return catalogue.cards(newest_first(containers))

    @override
    def upcoming(self) -> tuple[CardDTO, ...]:
        catalogue = self._catalogue()
        return catalogue.cards(self._upcoming(catalogue.of_role(TypeRole.CALENDAR)))
