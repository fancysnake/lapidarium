"""Repositories: the adapter's public surface, speaking DTOs and write dicts."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, override

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Prefetch

from lapidarium.links.db.django.models import (
    Entry,
    EntryType,
    FieldDefinition,
    Link,
    MediaAsset,
    Part,
    Profile,
    Relation,
    SyndicationLink,
    Tag,
)
from lapidarium.pacts import (
    AccountRepositoryProtocol,
    AssetData,
    DoorPick,
    EntryDTO,
    EntryRefDTO,
    EntryRepositoryProtocol,
    EntryStatus,
    EntryTypeDTO,
    EntryTypeRepositoryProtocol,
    FieldDefinitionDTO,
    FieldKind,
    Layout,
    LinkDTO,
    MediaAssetDTO,
    MediaAssetRepositoryProtocol,
    NotFoundError,
    PartDTO,
    PartKind,
    ProfileDTO,
    ProfileRepositoryProtocol,
    RelationDTO,
    SyndicationLinkDTO,
    TypeRole,
    UrlKind,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lapidarium.pacts import (
        EntryData,
        EntryTypeData,
        LinkData,
        ProfileData,
        RelationData,
    )


def field_dto(field: FieldDefinition) -> FieldDefinitionDTO:
    return FieldDefinitionDTO(
        key=field.key,
        label=field.label,
        kind=FieldKind(field.kind),
        required=field.required,
        choices=tuple(field.choices),
        url_kind=UrlKind(field.url_kind),
        target_type=field.target_type.key if field.target_type else "",
        show_on_card=field.show_on_card,
        show_in_metadata_panel=field.show_in_metadata_panel,
    )


def entry_type_dto(entry_type: EntryType) -> EntryTypeDTO:
    """Build from a type whose `fields` (with `target_type`) are loaded or loadable."""
    return EntryTypeDTO(
        key=entry_type.key,
        label=entry_type.label,
        label_plural=entry_type.label_plural,
        route=entry_type.route,
        colour=entry_type.colour,
        tint=entry_type.tint,
        icon=entry_type.icon,
        order=entry_type.order,
        in_menu=entry_type.in_menu,
        role=TypeRole(entry_type.role),
        layout=Layout(entry_type.layout),
        allowed_parts=tuple(entry_type.allowed_parts),
        required_parts=tuple(entry_type.required_parts),
        door_enabled=entry_type.door_enabled,
        door_label=entry_type.door_label,
        door_pick=DoorPick(entry_type.door_pick),
        door_min_entries=entry_type.door_min_entries,
        list_filters=tuple(entry_type.list_filters),
        has_detail_page=entry_type.has_detail_page,
        fields=tuple(field_dto(f) for f in entry_type.fields.all()),
    )


def asset_dto(asset: MediaAsset) -> MediaAssetDTO:
    return MediaAssetDTO(path=asset.file.name or "", url=asset.file.url, alt=asset.alt)


def _entry_dto(entry: Entry) -> EntryDTO:
    return EntryDTO(
        type_key=entry.type.key,
        slug=entry.slug,
        title=entry.title,
        summary=entry.summary,
        date=entry.date,
        start_at=entry.start_at,
        end_at=entry.end_at,
        location=entry.location,
        is_online=entry.is_online,
        external_url=entry.external_url,
        status=EntryStatus(entry.status),
        featured=entry.featured,
        hide_from_whats_new=entry.hide_from_whats_new,
        license=entry.license,
        outcome=entry.outcome,
        cover=asset_dto(entry.cover) if entry.cover else None,
        tags=tuple(tag.name for tag in entry.tags.all()),
        metadata=entry.metadata,
        parts=tuple(
            PartDTO(
                kind=PartKind(part.kind),
                text=part.text,
                url=part.url,
                asset=asset_dto(part.asset) if part.asset else None,
                caption=part.caption,
                options=part.options,
            )
            for part in entry.parts.all()
        ),
        relations=tuple(
            RelationDTO(
                role=relation.role,
                target=EntryRefDTO(
                    type_key=relation.to_entry.type.key,
                    slug=relation.to_entry.slug,
                    title=relation.to_entry.title,
                    status=EntryStatus(relation.to_entry.status),
                ),
            )
            for relation in entry.relations.all()
        ),
        syndication=tuple(
            SyndicationLinkDTO.model_validate(link) for link in entry.syndication.all()
        ),
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def _asset_by_path(path: str) -> MediaAsset | None:
    if not path:
        return None
    try:
        return MediaAsset.objects.get(file=path)
    except MediaAsset.DoesNotExist:
        raise NotFoundError(path) from None


def _put(path: str, content: bytes) -> None:
    # The path is the asset's identity in an export, so it is kept exactly.
    if default_storage.exists(path):
        default_storage.delete(path)
    default_storage.save(path, ContentFile(content))


class EntryTypeRepository(EntryTypeRepositoryProtocol):
    @override
    def list_all(self) -> list[EntryTypeDTO]:
        types = EntryType.objects.prefetch_related(
            Prefetch(
                "fields", queryset=FieldDefinition.objects.select_related("target_type")
            )
        )
        return [entry_type_dto(t) for t in types]

    @override
    def save_all(self, types: Sequence[EntryTypeData]) -> None:
        # Every type exists before any field points at one as its target.
        saved = {
            data["key"]: EntryType.objects.update_or_create(
                key=data["key"],
                defaults={k: v for k, v in data.items() if k != "fields"},
            )[0]
            for data in types
        }
        for data in types:
            entry_type = saved[data["key"]]
            entry_type.fields.all().delete()
            FieldDefinition.objects.bulk_create(
                FieldDefinition(
                    entry_type=entry_type,
                    order=order,
                    **{k: v for k, v in field.items() if k != "target_type"},
                    target_type=(
                        EntryType.objects.get(key=field["target_type"])
                        if field["target_type"]
                        else None
                    ),
                )
                for order, field in enumerate(data["fields"])
            )


class EntryRepository(EntryRepositoryProtocol):
    @override
    def list_published(self) -> list[EntryDTO]:
        entries = (
            Entry.objects.filter(status=EntryStatus.PUBLISHED)
            .select_related("type", "cover")
            .prefetch_related(
                "tags",
                "syndication",
                Prefetch("parts", queryset=Part.objects.select_related("asset")),
                Prefetch(
                    "relations",
                    queryset=Relation.objects.select_related("to_entry__type"),
                ),
            )
            .order_by("type__order", "type__key", "slug")
        )
        return [_entry_dto(entry) for entry in entries]

    @override
    def save(self, data: EntryData) -> None:
        excluded = {
            "type",
            "slug",
            "cover",
            "tags",
            "parts",
            "relations",
            "syndication",
            "created_at",
            "updated_at",
        }
        entry, _ = Entry.objects.update_or_create(
            type=EntryType.objects.get(key=data["type"]),
            slug=data["slug"],
            defaults={
                **{k: v for k, v in data.items() if k not in excluded},
                "cover": _asset_by_path(data["cover"]),
            },
        )
        entry.tags.set(Tag.objects.get_or_create(name=name)[0] for name in data["tags"])
        entry.parts.all().delete()
        Part.objects.bulk_create(
            Part(
                entry=entry,
                order=order,
                kind=part["kind"],
                text=part["text"],
                url=part["url"],
                asset=_asset_by_path(part["asset"]),
                caption=part["caption"],
                options=part["options"],
            )
            for order, part in enumerate(data["parts"])
        )
        entry.syndication.all().delete()
        SyndicationLink.objects.bulk_create(
            SyndicationLink(entry=entry, **link) for link in data["syndication"]
        )
        entry.refresh_search_text()
        stamps = {key: data[key] for key in ("created_at", "updated_at") if data[key]}
        if stamps:
            Entry.objects.filter(pk=entry.pk).update(**stamps)

    @override
    def set_relations(
        self, type_key: str, slug: str, *, relations: Sequence[RelationData]
    ) -> None:
        def entry(type_key: str, slug: str) -> Entry:
            try:
                return Entry.objects.get(type__key=type_key, slug=slug)
            except Entry.DoesNotExist:
                msg = f"{type_key}/{slug}"
                raise NotFoundError(msg) from None

        source = entry(type_key, slug)
        source.relations.all().delete()
        Relation.objects.bulk_create(
            Relation(
                from_entry=source,
                to_entry=entry(relation["target_type"], relation["target_slug"]),
                role=relation["role"],
                order=order,
            )
            for order, relation in enumerate(relations)
        )


class MediaAssetRepository(MediaAssetRepositoryProtocol):
    @override
    def read(self, path: str) -> bytes:
        with default_storage.open(path) as file:
            content: bytes = file.read()
        return content

    @override
    def save(self, data: AssetData) -> MediaAssetDTO:
        asset, _ = MediaAsset.objects.update_or_create(
            file=data["path"], defaults={"alt": data["alt"]}
        )
        # Storage is not transactional: files change only once the rows commit.
        transaction.on_commit(partial(_put, data["path"], data["content"]))
        return asset_dto(asset)


class ProfileRepository(ProfileRepositoryProtocol):
    @override
    def get(self) -> ProfileDTO | None:
        if (profile := Profile.objects.select_related("photo").first()) is None:
            return None
        return ProfileDTO(
            name=profile.name,
            handle=profile.handle,
            tagline=profile.tagline,
            photo=asset_dto(profile.photo) if profile.photo else None,
            bio=profile.bio,
            email=profile.email,
        )

    @override
    def list_links(self) -> list[LinkDTO]:
        return [LinkDTO.model_validate(link) for link in Link.objects.all()]

    @override
    def save(self, data: ProfileData) -> None:
        values = {**data, "photo": _asset_by_path(data["photo"])}
        if profile := Profile.objects.first():
            Profile.objects.filter(pk=profile.pk).update(**values)
        else:
            Profile.objects.create(**values)

    @override
    def replace_links(self, links: Sequence[LinkData]) -> None:
        Link.objects.all().delete()
        Link.objects.bulk_create(
            Link(order=order, **link) for order, link in enumerate(links)
        )


class AccountRepository(AccountRepositoryProtocol):
    @override
    def ensure_superuser(self, username: str, *, password: str) -> bool:
        user, created = get_user_model().objects.update_or_create(
            username=username,
            defaults={"is_active": True, "is_staff": True, "is_superuser": True},
        )
        user.set_password(password)
        user.save(update_fields=["password"])
        return created
