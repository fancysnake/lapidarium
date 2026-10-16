"""Type schemas: metadata, role built-ins, parts, relations, colours."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, override
from urllib.parse import urlsplit

from lapidarium.mills.colour import contrast_ratio, mix
from lapidarium.pacts import (
    BUILTIN_DEFAULTS,
    CONTAINER_ROLES,
    ROLE_BUILTINS,
    ROLE_REQUIRED,
    EntryStatus,
    EntryTypeDTO,
    FieldKind,
    MetadataValidationError,
    PartData,
    PartKind,
    RelationEndDTO,
    RelationRole,
    SchemaServiceProtocol,
    TypeRole,
    UrlKind,
)
from lapidarium.specs import (
    CONTRAST_FLOOR,
    GITHUB_HOSTS,
    ITCH_HOST,
    TINT_MIX,
    YOUTUBE_HOSTS,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence

    from lapidarium.pacts import (
        FieldDefinitionDTO,
        Metadata,
        MetadataInput,
        MetadataValue,
    )

_BLANK = frozenset({None, ""})


def _host(url: str) -> str | None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return None
    return parts.hostname


def _url_error(url: str, url_kind: UrlKind) -> str | None:
    if (host := _host(url)) is None:
        return "Enter a full http(s) address."
    match url_kind:
        case UrlKind.YOUTUBE if host not in YOUTUBE_HOSTS:
            return "Enter a YouTube address."
        case UrlKind.ITCH if host != ITCH_HOST and not host.endswith(f".{ITCH_HOST}"):
            return "Enter an itch.io address."
        case UrlKind.GITHUB if host not in GITHUB_HOSTS:
            return "Enter a GitHub address."
        case _:
            return None


type _Given = str | float | dt.date


def _clean_text(value: _Given, _field: FieldDefinitionDTO) -> str:
    return str(value).strip()


def _clean_url(value: _Given, field: FieldDefinitionDTO) -> str:
    url = str(value).strip()
    if error := _url_error(url, field.url_kind):
        raise ValueError(error)
    return url


def _clean_choice(value: _Given, field: FieldDefinitionDTO) -> str:
    if str(value) not in field.choices:
        msg = f"Choose one of: {', '.join(field.choices)}."
        raise ValueError(msg)
    return str(value)


def _clean_bool(value: _Given, _field: FieldDefinitionDTO) -> bool:
    if not isinstance(value, bool):
        msg = "Expected yes or no."
        raise TypeError(msg)
    return value


def _clean_number(value: _Given, _field: FieldDefinitionDTO) -> int | float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = "Expected a number."
        raise TypeError(msg)
    return int(value) if float(value).is_integer() else value


def _clean_date(value: _Given, _field: FieldDefinitionDTO) -> str:
    if isinstance(value, dt.date):
        return value.isoformat()
    try:
        return dt.date.fromisoformat(str(value)).isoformat()
    except ValueError:
        msg = "Expected a date (YYYY-MM-DD)."
        raise ValueError(msg) from None


# Every kind but `relation`, whose values are links rather than metadata.
_CLEANERS: Mapping[FieldKind, Callable[[_Given, FieldDefinitionDTO], MetadataValue]] = {
    FieldKind.TEXT: _clean_text,
    FieldKind.LONG_TEXT: _clean_text,
    FieldKind.URL: _clean_url,
    FieldKind.DATE: _clean_date,
    FieldKind.NUMBER: _clean_number,
    FieldKind.BOOL: _clean_bool,
    FieldKind.CHOICE: _clean_choice,
}


def _role_error(role: str, *, source: EntryTypeDTO, target: EntryTypeDTO) -> str | None:
    """Why entries of `source` cannot link to `target` as `role`, if they cannot."""
    if role == RelationRole.PART_OF:
        if target.role in CONTAINER_ROLES:
            return None
        return "Only containers can hold entries."
    if role in RelationRole:
        return None
    fields = (f for f in source.fields if f.kind == FieldKind.RELATION)
    if (field := next((f for f in fields if f.key == role), None)) is None:
        return f"Unknown relation role {role!r}."
    if target.key != field.target_type:
        return f"{field.label} cannot link to a {target.label}."
    return None


class SchemaService(SchemaServiceProtocol):
    """Type schemas: metadata, role built-ins, parts, colours."""

    def __init__(self, background: str, *, dark_background: str | None = None) -> None:
        self._background = background
        self._dark_background = dark_background

    @override
    def validate_metadata(
        self, entry_type: EntryTypeDTO, values: Mapping[str, MetadataInput]
    ) -> Metadata:
        fields = {f.key: f for f in entry_type.fields if f.kind in _CLEANERS}
        errors = {
            key: "Not a field of this type." for key in values if key not in fields
        }
        cleaned: Metadata = {}
        for key, field in fields.items():
            value = values.get(key)
            if value is None or not str(value):
                if field.required and field.kind.can_be_missing:
                    errors[key] = "This field is required."
                continue
            try:
                cleaned[key] = _CLEANERS[field.kind](value, field)
            except (TypeError, ValueError) as exc:
                errors[key] = str(exc)
        if errors:
            raise MetadataValidationError(errors)
        return cleaned

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
        if part["url"] and _host(part["url"]) is None:
            errors.append("Enter a full http(s) address.")
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
    def check_relation(
        self, role: str, *, source: RelationEndDTO, target: RelationEndDTO
    ) -> list[str]:
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
    def derive_tint(self, colour: str, *, dark: bool = False) -> str:
        background = (dark and self._dark_background) or self._background
        return mix(colour, background, share=TINT_MIX)

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
