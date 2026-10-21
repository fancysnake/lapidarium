"""Content as export format v1: export, import, local setup."""

from __future__ import annotations

import re
from functools import partial
from typing import TYPE_CHECKING, override

from lapidarium.pacts.catalogue import ListFilter
from lapidarium.pacts.content import (
    BundleValidationError,
    ContentBundle,
    ContentSummaryDTO,
    EntryData,
    EntryDTO,
    EntryStatus,
    ExportDTO,
    LocalSetupDTO,
    ProfileData,
    ProfileDTO,
    RelationEndDTO,
    RelationRole,
)
from lapidarium.pacts.schema import EntryTypeData, EntryTypeDTO, MetadataValidationError
from lapidarium.pacts.services import (
    ContentExportServiceProtocol,
    ContentImportServiceProtocol,
    LocalSetupServiceProtocol,
    SchemaServiceProtocol,
)
from lapidarium.specs import SLUG_PATTERN

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from lapidarium.pacts.content import (
        AccountRepositoryProtocol,
        ArchiveProtocol,
        ContentStoreProtocol,
        EntryRepositoryProtocol,
        MediaAssetRepositoryProtocol,
        ProfileRepositoryProtocol,
    )
    from lapidarium.pacts.db import TransactionProtocol
    from lapidarium.pacts.schema import EntryTypeRepositoryProtocol, Metadata

type _EntryKey = tuple[str, str]


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
        archive: ArchiveProtocol,
    ) -> None:
        self._types = types
        self._entries = entries
        self._assets = assets
        self._profile = profile
        self._store = store
        self._archive = archive

    @override
    def export(self, root: Path, *, commit: bool, push: bool) -> ExportDTO:
        if not (commit or push):
            return ExportDTO(content=self._write(root), committed=False)
        self._archive.check(root)
        content = self._write(root)
        committed = self._archive.commit(
            root,
            message=(
                f"Export: {content.entries} entries, {content.types} types,"
                f" {content.assets} assets"
            ),
        )
        if push and committed:
            self._archive.push(root)
        return ExportDTO(content=content, committed=committed)

    def _write(self, root: Path) -> ContentSummaryDTO:
        profile = self._profile.get()
        published = self._entries.list_published()
        if drafts := {
            f"content/{entry.type_key}/{entry.slug}.md": messages
            for entry in published
            if (messages := _draft_links(entry))
        }:
            raise BundleValidationError(drafts)
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


def _slug_errors(name: str, value: str) -> list[str]:
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


def _draft_links(entry: EntryDTO) -> list[str]:
    """Links the relation rules forbid; only data written around them has any."""
    return [
        f"Links to the draft {r.target.type_key}/{r.target.slug}."
        for r in entry.relations
        if r.target.status != EntryStatus.PUBLISHED
    ]


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
        schemas = {t["key"]: EntryTypeDTO.model_validate(t) for t in types}
        metadata = self._check(schemas, bundle)
        with self._transaction.atomic():
            for asset in bundle["assets"]:
                self._assets.save(asset)
                # Storage is not transactional: files change only once rows commit.
                self._transaction.on_commit(
                    partial(self._assets.write, asset["path"], content=asset["content"])
                )
            self._types.save_all(types)
            for entry in bundle["entries"]:
                key = (entry["type"], entry["slug"])
                self._entries.save({**entry, "metadata": metadata[key]})
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

    def _check(
        self, schemas: Mapping[str, EntryTypeDTO], bundle: ContentBundle
    ) -> dict[_EntryKey, Metadata]:
        """Each entry's cleaned metadata; `BundleValidationError` on any problem."""
        errors = {
            f"types/{type_key}.yaml": messages
            for type_key, schema in schemas.items()
            if (
                messages := [
                    *_slug_errors("Key", type_key),
                    *self._schema.check_colours(schema.colour, schema.tint),
                    *_filter_errors(schema),
                ]
            )
        }
        alts = {a["path"]: a["alt"] for a in bundle["assets"]}
        entries = {
            (e["type"], e["slug"]): e for e in bundle["entries"] if e["type"] in schemas
        }
        metadata: dict[_EntryKey, Metadata] = {}
        for entry in bundle["entries"]:
            key = (entry["type"], entry["slug"])
            where = f"content/{entry['type']}/{entry['slug']}.md"
            if (entry_type := schemas.get(entry["type"])) is None:
                errors[where] = [f"Unknown type {entry['type']!r}."]
                continue
            messages = []
            try:
                metadata[key] = self._schema.validate_metadata(
                    entry_type, entry["metadata"]
                )
            except MetadataValidationError as exc:
                messages.extend(f"metadata.{k}: {m}" for k, m in exc.errors.items())
            messages.extend(self._entry_errors(entry, entry_type, alts=alts))
            messages.extend(
                self._relation_errors(key, schemas=schemas, entries=entries)
            )
            if messages:
                errors[where] = messages
        profile = bundle["profile"]
        if profile and profile["photo"] and profile["photo"] not in alts:
            errors["profile.yaml"] = ["Photo is not among the assets."]
        if errors:
            raise BundleValidationError(errors)
        return metadata

    def _relation_errors(
        self,
        key: _EntryKey,
        *,
        schemas: Mapping[str, EntryTypeDTO],
        entries: Mapping[_EntryKey, EntryData],
    ) -> list[str]:
        def containers(keys: set[_EntryKey]) -> list[_EntryKey]:
            return [
                (r["target_type"], r["target_slug"])
                for k in keys
                if k in entries
                for r in entries[k]["relations"]
                if r["role"] == RelationRole.PART_OF
            ]

        entry = entries[key]
        source = RelationEndDTO(entry_type=schemas[key[0]], status=entry["status"])
        links = [
            (r["role"], (r["target_type"], r["target_slug"]))
            for r in entry["relations"]
        ]
        messages: list[str] = []
        for role, target in links:
            if target == key:
                messages.append("Relation to itself.")
            elif (linked := entries.get(target)) is None:
                messages.append(f"Relation to missing {'/'.join(target)}.")
            else:
                end = RelationEndDTO(
                    entry_type=schemas[target[0]], status=linked["status"]
                )
                found = [
                    *self._schema.check_relation(role, source=source, target=end),
                    *self._schema.check_loop(
                        role, entry=key, target=target, containers=containers
                    ),
                ]
                messages.extend(f"Relation to {'/'.join(target)}: {m}" for m in found)
        roles = [role for role, _ in links]
        messages.extend(self._schema.check_relation_roles(source.entry_type, roles))
        return messages

    def _entry_errors(
        self, entry: EntryData, entry_type: EntryTypeDTO, *, alts: Mapping[str, str]
    ) -> list[str]:
        messages = _slug_errors("Slug", entry["slug"])
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
        return messages


class LocalSetupService(LocalSetupServiceProtocol):
    """Demo content plus an admin login: a local instance ready to click through."""

    def __init__(
        self,
        *,
        content_import: ContentImportServiceProtocol,
        transaction: TransactionProtocol,
        accounts: AccountRepositoryProtocol,
    ) -> None:
        self._content_import = content_import
        self._transaction = transaction
        self._accounts = accounts

    @override
    def set_up(self, demo: str, *, username: str, password: str) -> LocalSetupDTO:
        with self._transaction.atomic():
            content = self._content_import.load_demo(demo)
            created = self._accounts.ensure_superuser(username, password=password)
        return LocalSetupDTO(content=content, superuser_created=created)
