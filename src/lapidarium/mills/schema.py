"""Type schemas: role built-ins, parts, relations, colours, routes."""

from __future__ import annotations

import datetime as dt
import re
from typing import TYPE_CHECKING, override
from urllib.parse import urlsplit

from lapidarium.mills.colour import (
    WHITE,
    contrast_ratio,
    lowest_contrast,
    mix,
    tint_over,
)
from lapidarium.pacts.content import (
    BUILTIN_DEFAULTS,
    CONTAINER_ROLES,
    ROLE_BUILTINS,
    ROLE_REQUIRED,
    EntryStatus,
    EntryTypeDTO,
    FieldKind,
    ListFilter,
    PartData,
    PartKind,
    RelationEndDTO,
    RelationRole,
    TypeRole,
    role_label,
)
from lapidarium.pacts.services import SchemaServiceProtocol
from lapidarium.specs import CONTRAST_FLOOR, SLUG_PATTERN

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence

_BLANK = frozenset({None, ""})
_LIGHTEN_STEPS = 100
# Pages ask per request; the colours and the background change per process.
_LIGHTENED: dict[tuple[str, str], str] = {}


def _lift(colour: str, background: str) -> str:
    """Return the least white that lifts `colour` over `background` and its tint.

    White itself when nothing reads; the theme check reports that background.
    """
    for step in range(_LIGHTEN_STEPS + 1):
        candidate = mix(WHITE, colour, share=step / _LIGHTEN_STEPS)
        tint = tint_over(candidate, background)
        ratio = lowest_contrast(candidate, background=background, tint=tint)
        if ratio >= CONTRAST_FLOOR:
            return candidate
    return WHITE


def _lighten(colour: str, background: str) -> str:
    if (key := (colour, background)) not in _LIGHTENED:
        _LIGHTENED[key] = _lift(colour, background)
    return _LIGHTENED[key]


def url_host(url: str) -> str | None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return None
    return parts.hostname


def url_errors(url: str) -> list[str]:
    """Errors unless `url` is a full http(s) address."""
    return [] if url_host(url) else ["Enter a full http(s) address."]


def slug_errors(name: str, value: str) -> list[str]:
    """Keys and slugs become file names on export, so they stay plain slugs."""
    if re.fullmatch(SLUG_PATTERN, value):
        return []
    return [f"{name} {value!r} may hold only letters, digits, - and _."]


def _filter_errors(entry_type: EntryTypeDTO) -> list[str]:
    fields = {f.key for f in entry_type.fields}
    return [
        f"List filter {key!r} is neither year, tag nor one of the fields."
        for key in entry_type.list_filters
        if key not in ListFilter and key not in fields
    ]


def _part_errors(entry_type: EntryTypeDTO) -> list[str]:
    if set(entry_type.required_parts) <= set(entry_type.allowed_parts):
        return []
    return ["Required parts must be allowed."]


def type_errors(schema: SchemaServiceProtocol, entry_type: EntryTypeDTO) -> list[str]:
    """Errors in a type's own settings: key, colours, route, filters, parts."""
    return [
        *slug_errors("Key", entry_type.key),
        *schema.check_colours(entry_type.colour, entry_type.tint),
        *schema.check_route(entry_type.route),
        *_filter_errors(entry_type),
        *_part_errors(entry_type),
    ]


def _role_error(role: str, *, source: EntryTypeDTO, target: EntryTypeDTO) -> str | None:
    """Why entries of `source` cannot link to `target` as `role`, a role it knows."""
    if role == RelationRole.PART_OF:
        if target.role in CONTAINER_ROLES:
            return None
        return "Only containers can hold entries."
    if role in RelationRole:
        return None
    fields = (f for f in source.fields if f.kind == FieldKind.RELATION)
    field = next(f for f in fields if f.key == role)
    if target.key != field.target_type:
        return f"{field.label} cannot link to a {target.label}."
    return None


# First path segments of the fixed pages, which no type's route may take.
_FIXED_PAGES: Mapping[str, str] = {
    "about": "the about page",
    "new": "the what's new page",
    "search": "the search page",
    "newsletter": "the newsletter page",
    "contact": "the contact page",
    "healthz": "the health probe",
}


def _first_segment(prefix: str) -> str | None:
    """First path segment of a URL prefix; `None` when another host serves it."""
    parts = urlsplit(prefix)
    if parts.netloc:
        return None
    return parts.path.strip("/").split("/")[0] or None


class SchemaService(SchemaServiceProtocol):
    """Type schemas: role built-ins, parts, relations, colours, routes.

    Type colours get a dark-scheme variant when `dark_background` is given.
    A type's route cannot start a fixed page, nor the admin, upload or static
    URL prefix the deployment serves.
    """

    def __init__(
        self,
        background: str,
        *,
        dark_background: str | None,
        admin_url: str,
        media_url: str,
        static_url: str,
    ) -> None:
        self._background = background
        self._dark_background = dark_background
        served = {
            admin_url: "the admin",
            media_url: "uploads",
            static_url: "static files",
        }
        self._taken_routes: dict[str, str] = {
            **{
                segment: owner
                for prefix, owner in served.items()
                if (segment := _first_segment(prefix))
            },
            **_FIXED_PAGES,
        }

    @override
    def check_builtins(
        self, role: TypeRole, values: Mapping[str, object]
    ) -> dict[str, str]:
        errors: dict[str, str] = {}
        for key in BUILTIN_DEFAULTS:
            value = values.get(key)
            if key not in ROLE_BUILTINS[role] and value not in {*_BLANK, False}:
                errors[key] = f"Not used by the {role} role."
            elif key in ROLE_REQUIRED[role] and value in _BLANK:
                errors[key] = "This field is required."
        start, end = values.get("start_at"), values.get("end_at")
        if (
            isinstance(start, dt.datetime)
            and isinstance(end, dt.datetime)
            and end < start
            and "end_at" not in errors
        ):
            errors["end_at"] = "Ends before it starts."
        return errors

    @override
    def check_part(self, part: PartData, asset_alt: str | None) -> list[str]:
        kind = part["kind"]
        has_asset = asset_alt is not None
        errors: list[str] = []
        match kind:
            case PartKind.TEXT if not part["text"].strip():
                errors.append("A text part needs text.")
            case PartKind.VIDEO | PartKind.LINK if not part["url"]:
                errors.append(f"A {kind} part needs a URL.")
            case PartKind.AUDIO if not part["url"] and not has_asset:
                errors.append("An audio part needs a URL or a file.")
            case PartKind.IMAGE | PartKind.FILE if not has_asset:
                errors.append(f"The {kind} part needs an uploaded file.")
            case PartKind.IMAGE if not asset_alt:
                errors.append("An image part needs alt text on its asset.")
            case _:
                pass
        if part["url"]:
            errors.extend(url_errors(part["url"]))
        return errors

    @override
    def check_part_kinds(
        self, entry_type: EntryTypeDTO, kinds: Sequence[PartKind]
    ) -> list[str]:
        errors = [
            f"{entry_type.label} does not allow {kind} parts."
            for kind in dict.fromkeys(kinds, True)
            if kind not in entry_type.allowed_parts
        ]
        errors.extend(
            f"{entry_type.label} needs at least one {kind} part."
            for kind in entry_type.required_parts
            if kind not in kinds
        )
        return errors

    @override
    def relation_roles(self, entry_type: EntryTypeDTO) -> dict[str, str]:
        builtin = {role.value: role_label(role) for role in RelationRole}
        fields = (f for f in entry_type.fields if f.kind == FieldKind.RELATION)
        return builtin | {f.key: f.label for f in fields}

    @override
    def check_relation(
        self, role: str, *, source: RelationEndDTO, target: RelationEndDTO
    ) -> list[str]:
        if role not in self.relation_roles(source.entry_type):
            return [f"Unknown relation role {role!r}."]
        errors: list[str] = []
        if error := _role_error(
            role, source=source.entry_type, target=target.entry_type
        ):
            errors.append(error)
        if source.status == EntryStatus.PUBLISHED != target.status:
            errors.append("A published entry cannot link to a draft.")
        return errors

    @override
    def check_loop[K: Hashable](
        self,
        role: str,
        *,
        entry: K,
        target: K,
        containers: Callable[[set[K]], Iterable[K]],
    ) -> list[str]:
        if role != RelationRole.PART_OF:
            return []
        seen: set[K] = set()
        frontier = {target}
        while frontier:
            if entry in frontier:
                return ["That makes a loop of containers."]
            seen |= frontier
            frontier = set(containers(frontier)) - seen
        return []

    @override
    def check_relation_roles(
        self, entry_type: EntryTypeDTO, roles: Iterable[str]
    ) -> list[str]:
        linked = set(roles)
        if missing := [
            f.label
            for f in entry_type.fields
            if f.kind == FieldKind.RELATION and f.required and f.key not in linked
        ]:
            return [f"Link at least one entry as: {', '.join(missing)}."]
        return []

    @override
    def derive_tint(self, colour: str) -> str:
        return tint_over(colour, self._background)

    @override
    def check_colours(self, colour: str, tint: str) -> list[str]:
        errors: list[str] = []
        if (ratio := contrast_ratio(colour, self._background)) < CONTRAST_FLOOR:
            errors.append(
                f"Contrast with the page background is {ratio:.2f}:1,"
                f" needs {CONTRAST_FLOOR}:1."
            )
        if (ratio := contrast_ratio(colour, tint)) < CONTRAST_FLOOR:
            errors.append(
                f"Contrast with the tint is {ratio:.2f}:1, needs {CONTRAST_FLOOR}:1."
            )
        return errors

    @override
    def check_route(self, route: str) -> list[str]:
        if (owner := self._taken_routes.get(route)) is None:
            return []
        return [f"/{route}/ belongs to {owner}."]

    @override
    def derive_dark_colour(self, colour: str) -> str | None:
        if (dark := self._dark_background) is None:
            return None
        return _lighten(colour, dark)
