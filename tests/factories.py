"""Write shapes and DTOs with every key filled, for tests to override what matters."""

import datetime as dt

from lapidarium.pacts.content import (
    BUILTIN_DEFAULTS,
    EntryDTO,
    EntryRefDTO,
    EntryStatus,
    EntryTypeDTO,
    FieldDefinitionDTO,
    FieldKind,
    PartKind,
    RelationDTO,
    ShowcaseDTO,
    TypeRole,
    UrlKind,
)
from lapidarium.pacts.site import ProfileDTO


def type_data(key="session", **overrides):
    return {
        "allowed_parts": [PartKind.TEXT, PartKind.IMAGE],
        "colour": "#6b3fa0",
        "door_enabled": False,
        "door_label": "",
        "door_min_entries": 1,
        "door_pick": "latest",
        "fields": [],
        "has_detail_page": True,
        "icon": "",
        "in_menu": True,
        "key": key,
        "label": key.title(),
        "label_plural": f"{key.title()}s",
        "layout": "article",
        "list_filters": [],
        "order": 0,
        "required_parts": [],
        "role": TypeRole.THING,
        "route": f"{key}s",
        "tint": "",
        **overrides,
    }


def field_data(key, kind=FieldKind.TEXT, **overrides):
    return {
        "choices": [],
        "key": key,
        "kind": kind,
        "label": key.title(),
        "required": False,
        "show_in_metadata_panel": True,
        "show_on_card": False,
        "target_type": "",
        "url_kind": UrlKind.ANY_HOST,
        **overrides,
    }


def part_data(kind=PartKind.TEXT, **overrides):
    return {
        "asset": "",
        "caption": "",
        "kind": kind,
        "options": {},
        "text": "",
        "url": "",
        **overrides,
    }


def builtins(**overrides):
    return {**BUILTIN_DEFAULTS, **overrides}


def entry_data(slug="moose", entry_type="session", **overrides):
    defaults = {
        "cover": "",
        "created_at": None,
        "external_url": "",
        "featured": False,
        "hide_from_whats_new": False,
        "license": "",
        "metadata": {},
        "parts": [],
        "relations": [],
        "slug": slug,
        "status": EntryStatus.PUBLISHED,
        "summary": "One sentence.",
        "syndication": [],
        "tags": [],
        "title": slug.title(),
        "type": entry_type,
        "updated_at": None,
    }
    return builtins(**(defaults | overrides))


NOW = dt.datetime(2026, 10, 14, 12, tzinfo=dt.UTC)


def field_dto(key, kind=FieldKind.TEXT, **overrides):
    return FieldDefinitionDTO(**field_data(key, kind, **overrides))


def type_dto(key="session", *, fields=(), **overrides):
    return EntryTypeDTO(
        **type_data(key, fields=fields, **{"tint": "#eeeeee", **overrides})
    )


def ref_dto(slug, type_key="session", *, status=EntryStatus.PUBLISHED):
    return EntryRefDTO(type_key=type_key, slug=slug, title=slug.title(), status=status)


def relation_dto(role, slug, *, type_key="session"):
    return RelationDTO(role=role, target=ref_dto(slug, type_key))


def entry_dto(slug="moose", type_key="session", **overrides):
    return EntryDTO(
        **{
            **BUILTIN_DEFAULTS,
            "type_key": type_key,
            "slug": slug,
            "title": slug.title(),
            "summary": "One sentence.",
            "external_url": "",
            "status": EntryStatus.PUBLISHED,
            "featured": False,
            "hide_from_whats_new": False,
            "license": "",
            "cover": None,
            "tags": (),
            "metadata": {},
            "parts": (),
            "relations": (),
            "syndication": (),
            "created_at": NOW - dt.timedelta(days=30),
            "updated_at": NOW - dt.timedelta(days=30),
            **overrides,
        }
    )


def profile_dto(**overrides):
    return ProfileDTO(
        **{
            "name": "Mira",
            "handle": "",
            "tagline": "",
            "photo": None,
            "bio": "",
            "email": "mira@example.com",
            "button": None,
            "friends_title": "",
            "friends_intro": "",
            **overrides,
        }
    )


def profile_data(**overrides):
    blank = ("handle", "tagline", "photo", "bio", "email", "button")
    return {
        "name": "Mira",
        **dict.fromkeys((*blank, "friends_title", "friends_intro"), ""),
        **overrides,
    }


def showcase_dto(title="Start here", *, entries=(), **overrides):
    return ShowcaseDTO(
        **{
            "title": title,
            "intro": "",
            "hidden": False,
            "entries": entries,
            **overrides,
        }
    )


def showcase_data(title="Start here", *, entries=(), **overrides):
    return {
        "title": title,
        "intro": "",
        "hidden": False,
        "entries": [{"type": type_key, "slug": slug} for type_key, slug in entries],
        **overrides,
    }
