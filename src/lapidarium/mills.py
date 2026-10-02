"""Business logic. No framework, no IO."""

from __future__ import annotations

import datetime as dt
import math
from typing import TYPE_CHECKING, override
from urllib.parse import urlsplit

from lapidarium.pacts import (
    CONTAINER_ROLES,
    ROLE_BUILTINS,
    ROLE_REQUIRED,
    BundleValidationError,
    ContentBundle,
    ContentExportServiceProtocol,
    ContentImportServiceProtocol,
    ContentSummaryDTO,
    EntryData,
    EntryDTO,
    EntryStatus,
    EntryTypeData,
    EntryTypeDTO,
    FieldDefinitionDTO,
    FieldKind,
    MetadataValidationError,
    PartData,
    PartKind,
    ProfileData,
    ProfileDTO,
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
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path

    from lapidarium.pacts import (
        BuiltinValues,
        ContentStoreProtocol,
        EntryRepositoryProtocol,
        EntryTypeRepositoryProtocol,
        MediaAssetRepositoryProtocol,
        Metadata,
        MetadataInput,
        MetadataValue,
        ProfileRepositoryProtocol,
        TransactionProtocol,
    )

_LINEAR_THRESHOLD = 0.04045
_BLANK = frozenset({None, ""})


def _rgb(colour: str) -> tuple[int, int, int]:
    value = colour.removeprefix("#")
    red, green, blue = (int(value[i : i + 2], 16) for i in range(0, 6, 2))
    return red, green, blue


def _luminance(colour: str) -> float:
    def linear(channel: int) -> float:
        if (srgb := channel / 255) <= _LINEAR_THRESHOLD:
            return srgb / 12.92
        return math.pow((srgb + 0.055) / 1.055, 2.4)

    red, green, blue = (linear(c) for c in _rgb(colour))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first: str, second: str) -> float:
    """WCAG contrast ratio of two `#rrggbb` colours."""
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def mix(colour: str, background: str, *, share: float) -> str:
    """`share` of `colour` laid over `background`, as `#rrggbb`."""
    channels = zip(_rgb(colour), _rgb(background), strict=True)
    mixed = (round(c * share + b * (1 - share)) for c, b in channels)
    return "#" + "".join(f"{c:02x}" for c in mixed)


def _host(url: str) -> str | None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return None
    return parts.hostname


def _clean_bool(value: str | float | dt.date) -> bool:
    if not isinstance(value, bool):
        msg = "Expected yes or no."
        raise TypeError(msg)
    return value


def _clean_number(value: str | float | dt.date) -> int | float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = "Expected a number."
        raise TypeError(msg)
    return int(value) if float(value).is_integer() else value


def _clean_date(value: str | float | dt.date) -> str:
    if isinstance(value, dt.date):
        return value.isoformat()
    try:
        return dt.date.fromisoformat(str(value)).isoformat()
    except ValueError:
        msg = "Expected a date (YYYY-MM-DD)."
        raise ValueError(msg) from None


_CLEANERS: Mapping[FieldKind, Callable[[str | float | dt.date], MetadataValue]] = {
    FieldKind.BOOL: _clean_bool,
    FieldKind.NUMBER: _clean_number,
    FieldKind.DATE: _clean_date,
}


class SchemaService(SchemaServiceProtocol):
    """Type schemas: metadata, role built-ins, parts, colours."""

    def __init__(self, background: str) -> None:
        self._background = background

    @override
    def check_url(self, url: str, url_kind: UrlKind) -> str | None:
        if (host := _host(url)) is None:
            return "Enter a full http(s) address."
        match url_kind:
            case UrlKind.YOUTUBE if host not in YOUTUBE_HOSTS:
                return "Enter a YouTube address."
            case UrlKind.ITCH if host != ITCH_HOST and not host.endswith(
                f".{ITCH_HOST}"
            ):
                return "Enter an itch.io address."
            case UrlKind.GITHUB if host not in GITHUB_HOSTS:
                return "Enter a GitHub address."
            case _:
                return None

    @override
    def validate_metadata(
        self, entry_type: EntryTypeDTO, values: Mapping[str, MetadataInput]
    ) -> Metadata:
        fields = {f.key: f for f in entry_type.fields if f.kind != FieldKind.RELATION}
        errors = {
            key: "Not a field of this type." for key in values if key not in fields
        }
        cleaned: Metadata = {}
        for key, field in fields.items():
            value = values.get(key)
            if value is None or not str(value):
                if field.required and field.kind != FieldKind.BOOL:
                    errors[key] = "This field is required."
                continue
            try:
                cleaned[key] = self._clean_value(
                    field.kind, value, choices=field.choices
                )
            except (TypeError, ValueError) as exc:
                errors[key] = str(exc)
                continue
            if field.kind == FieldKind.URL and (
                error := self.check_url(str(cleaned[key]), field.url_kind)
            ):
                errors[key] = error
        if errors:
            raise MetadataValidationError(errors)
        return cleaned

    @staticmethod
    def _clean_value(
        kind: FieldKind, value: str | float | dt.date, *, choices: Sequence[str]
    ) -> MetadataValue:
        if kind == FieldKind.CHOICE and str(value) not in choices:
            msg = f"Choose one of: {', '.join(choices)}."
            raise ValueError(msg)
        cleaner = _CLEANERS.get(kind)
        return cleaner(value) if cleaner else str(value).strip()

    @override
    def check_builtins(self, role: TypeRole, values: BuiltinValues) -> dict[str, str]:
        given: dict[str, dt.date | str | bool | None] = {
            "date": values["date"],
            "start_at": values["start_at"],
            "end_at": values["end_at"],
            "location": values["location"],
            "is_online": values["is_online"],
            "outcome": values["outcome"],
        }
        errors: dict[str, str] = {}
        for key, value in given.items():
            if key not in ROLE_BUILTINS[role] and value not in {*_BLANK, False}:
                errors[key] = f"Not used by the {role} role."
            elif key in ROLE_REQUIRED[role] and value in _BLANK:
                errors[key] = "This field is required."
        start, end = values["start_at"], values["end_at"]
        if start and end and end < start and "end_at" not in errors:
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
    def derive_tint(self, colour: str) -> str:
        return mix(colour, self._background, share=TINT_MIX)

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


def entry_to_data(entry: EntryDTO) -> EntryData:
    return {
        "type": entry.type_key,
        "slug": entry.slug,
        "title": entry.title,
        "summary": entry.summary,
        "date": entry.date,
        "start_at": entry.start_at,
        "end_at": entry.end_at,
        "location": entry.location,
        "is_online": entry.is_online,
        "external_url": entry.external_url,
        "status": entry.status,
        "featured": entry.featured,
        "hide_from_whats_new": entry.hide_from_whats_new,
        "license": entry.license,
        "outcome": entry.outcome,
        "cover": entry.cover.path if entry.cover else "",
        "tags": list(entry.tags),
        "metadata": dict(entry.metadata),
        "parts": [
            {
                "kind": part.kind,
                "text": part.text,
                "url": part.url,
                "asset": part.asset.path if part.asset else "",
                "caption": part.caption,
                "options": dict(part.options),
            }
            for part in entry.parts
        ],
        "relations": [
            {
                "role": relation.role,
                "target_type": relation.target.type_key,
                "target_slug": relation.target.slug,
            }
            for relation in entry.relations
            if relation.target.status == EntryStatus.PUBLISHED
        ],
        "syndication": [
            {"platform": link.platform, "url": link.url} for link in entry.syndication
        ],
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }


def type_to_data(entry_type: EntryTypeDTO) -> EntryTypeData:
    return {
        "key": entry_type.key,
        "label": entry_type.label,
        "label_plural": entry_type.label_plural,
        "route": entry_type.route,
        "colour": entry_type.colour,
        "tint": entry_type.tint,
        "icon": entry_type.icon,
        "order": entry_type.order,
        "in_menu": entry_type.in_menu,
        "role": entry_type.role,
        "layout": entry_type.layout,
        "allowed_parts": list(entry_type.allowed_parts),
        "required_parts": list(entry_type.required_parts),
        "door_enabled": entry_type.door_enabled,
        "door_label": entry_type.door_label,
        "door_pick": entry_type.door_pick,
        "door_min_entries": entry_type.door_min_entries,
        "list_filters": list(entry_type.list_filters),
        "has_detail_page": entry_type.has_detail_page,
        "fields": [
            {
                "key": field.key,
                "label": field.label,
                "kind": field.kind,
                "required": field.required,
                "choices": list(field.choices),
                "url_kind": field.url_kind,
                "target_type": field.target_type,
                "show_on_card": field.show_on_card,
                "show_in_metadata_panel": field.show_in_metadata_panel,
            }
            for field in entry_type.fields
        ],
    }


class ContentExportService(ContentExportServiceProtocol):
    """Published content, its types and the assets it uses, as export format v1."""

    def __init__(
        self,
        *,
        types: EntryTypeRepositoryProtocol,
        entries: EntryRepositoryProtocol,
        assets: MediaAssetRepositoryProtocol,
        profile: ProfileRepositoryProtocol,
        store: ContentStoreProtocol,
    ) -> None:
        self._types = types
        self._entries = entries
        self._assets = assets
        self._profile = profile
        self._store = store

    @override
    def export(self, root: Path) -> ContentSummaryDTO:
        profile = self._profile.get()
        published = self._entries.list_published()
        alts: dict[str, str] = {}
        if profile and profile.photo:
            alts[profile.photo.path] = profile.photo.alt
        for entry in published:
            assets = [entry.cover, *(part.asset for part in entry.parts)]
            alts.update((asset.path, asset.alt) for asset in assets if asset)
        bundle: ContentBundle = {
            "profile": _profile_to_data(profile) if profile else None,
            "links": [
                {"platform": link.platform, "url": link.url, "label": link.label}
                for link in self._profile.list_links()
            ],
            "types": [type_to_data(t) for t in self._types.list_all()],
            "entries": [entry_to_data(entry) for entry in published],
            "assets": [
                {"path": path, "alt": alt, "content": self._assets.read(path)}
                for path, alt in sorted(alts.items())
            ],
        }
        self._store.write(root, bundle)
        return _summary(bundle)


def _profile_to_data(profile: ProfileDTO) -> ProfileData:
    return {
        "name": profile.name,
        "handle": profile.handle,
        "tagline": profile.tagline,
        "photo": profile.photo.path if profile.photo else "",
        "bio": profile.bio,
        "email": profile.email,
    }


def _summary(bundle: ContentBundle) -> ContentSummaryDTO:
    return ContentSummaryDTO(
        types=len(bundle["types"]),
        entries=len(bundle["entries"]),
        assets=len(bundle["assets"]),
    )


class ContentImportService(ContentImportServiceProtocol):
    """Validate an export bundle against its own types, then upsert it whole."""

    def __init__(
        self,
        *,
        schema: SchemaServiceProtocol,
        transaction: TransactionProtocol,
        types: EntryTypeRepositoryProtocol,
        entries: EntryRepositoryProtocol,
        assets: MediaAssetRepositoryProtocol,
        profile: ProfileRepositoryProtocol,
        store: ContentStoreProtocol,
    ) -> None:
        self._schema = schema
        self._transaction = transaction
        self._types = types
        self._entries = entries
        self._assets = assets
        self._profile = profile
        self._store = store

    @override
    def import_from(self, root: Path) -> ContentSummaryDTO:
        return self._load(self._store.read(root))

    @override
    def demo_names(self) -> tuple[str, ...]:
        return self._store.demo_names()

    @override
    def load_demo(self, name: str) -> ContentSummaryDTO:
        return self._load(self._store.read_demo(name))

    def _load(self, bundle: ContentBundle) -> ContentSummaryDTO:
        types = [self._with_tint(t) for t in bundle["types"]]
        schemas = {t["key"]: _type_dto(t, pk=pk) for pk, t in enumerate(types)}
        self._check(schemas, bundle)
        with self._transaction.atomic():
            for asset in bundle["assets"]:
                self._assets.save(asset)
            self._types.save_all(types)
            for entry in bundle["entries"]:
                schema = schemas[entry["type"]]
                self._entries.save(self._with_clean_metadata(entry, schema))
            for entry in bundle["entries"]:
                self._entries.set_relations(
                    entry["type"], entry["slug"], relations=entry["relations"]
                )
            if bundle["profile"]:
                self._profile.save(bundle["profile"])
            self._profile.replace_links(bundle["links"])
        return _summary(bundle)

    def _with_tint(self, entry_type: EntryTypeData) -> EntryTypeData:
        if entry_type["tint"]:
            return entry_type
        return {**entry_type, "tint": self._schema.derive_tint(entry_type["colour"])}

    def _with_clean_metadata(
        self, entry: EntryData, entry_type: EntryTypeDTO
    ) -> EntryData:
        metadata = self._schema.validate_metadata(entry_type, entry["metadata"])
        return {**entry, "metadata": metadata}

    def _check(
        self, schemas: Mapping[str, EntryTypeDTO], bundle: ContentBundle
    ) -> None:
        errors: dict[str, list[str]] = {}
        for entry_type in schemas.values():
            if messages := self._schema.check_colours(
                entry_type.colour, entry_type.tint
            ):
                errors[f"types/{entry_type.key}.yaml"] = messages
        alts = {a["path"]: a["alt"] for a in bundle["assets"]}
        slugs = {
            (e["type"], e["slug"]) for e in bundle["entries"] if e["type"] in schemas
        }
        for entry in bundle["entries"]:
            where = f"content/{entry['type']}/{entry['slug']}.md"
            if messages := self._entry_errors(
                entry, schemas=schemas, alts=alts, slugs=slugs
            ):
                errors[where] = messages
        profile = bundle["profile"]
        if profile and profile["photo"] and profile["photo"] not in alts:
            errors["profile.yaml"] = ["Photo is not among the assets."]
        if errors:
            raise BundleValidationError(errors)

    def _entry_errors(
        self,
        entry: EntryData,
        *,
        schemas: Mapping[str, EntryTypeDTO],
        alts: Mapping[str, str],
        slugs: set[tuple[str, str]],
    ) -> list[str]:
        if (entry_type := schemas.get(entry["type"])) is None:
            return [f"Unknown type {entry['type']!r}."]
        messages: list[str] = []
        try:
            self._schema.validate_metadata(entry_type, entry["metadata"])
        except MetadataValidationError as exc:
            messages.extend(f"metadata.{k}: {m}" for k, m in exc.errors.items())
        builtins = self._schema.check_builtins(entry_type.role, entry)
        messages.extend(f"{k}: {m}" for k, m in builtins.items())
        if entry["cover"] and entry["cover"] not in alts:
            messages.append(f"Cover {entry['cover']!r} is not among the assets.")
        for part in entry["parts"]:
            if part["asset"] and part["asset"] not in alts:
                messages.append(f"Asset {part['asset']!r} is not among the assets.")
                continue
            alt = alts[part["asset"]] if part["asset"] else None
            messages.extend(self._schema.check_part(part, alt))
        kinds = [part["kind"] for part in entry["parts"]]
        messages.extend(self._schema.check_part_kinds(entry_type, kinds))
        for relation in entry["relations"]:
            target = (relation["target_type"], relation["target_slug"])
            if target not in slugs:
                messages.append(f"Relation to missing {'/'.join(target)}.")
            elif (
                relation["role"] == RelationRole.PART_OF
                and schemas[target[0]].role not in CONTAINER_ROLES
            ):
                messages.append(f"part_of target {'/'.join(target)} is no container.")
        return messages


def _type_dto(data: EntryTypeData, *, pk: int) -> EntryTypeDTO:
    """Build the schema view of a type that so far exists only in a bundle."""
    return EntryTypeDTO(
        pk=pk,
        key=data["key"],
        label=data["label"],
        label_plural=data["label_plural"],
        route=data["route"],
        colour=data["colour"],
        tint=data["tint"],
        icon=data["icon"],
        order=data["order"],
        in_menu=data["in_menu"],
        role=data["role"],
        layout=data["layout"],
        allowed_parts=tuple(data["allowed_parts"]),
        required_parts=tuple(data["required_parts"]),
        door_enabled=data["door_enabled"],
        door_label=data["door_label"],
        door_pick=data["door_pick"],
        door_min_entries=data["door_min_entries"],
        list_filters=tuple(data["list_filters"]),
        has_detail_page=data["has_detail_page"],
        fields=tuple(
            FieldDefinitionDTO(
                key=field["key"],
                label=field["label"],
                kind=field["kind"],
                required=field["required"],
                choices=tuple(field["choices"]),
                url_kind=field["url_kind"],
                target_type=field["target_type"],
                show_on_card=field["show_on_card"],
                show_in_metadata_panel=field["show_in_metadata_panel"],
                order=order,
            )
            for order, field in enumerate(data["fields"])
        ),
    )
