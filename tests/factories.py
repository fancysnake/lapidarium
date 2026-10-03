"""Write shapes with every key filled, for tests to override what they care about."""

from lapidarium.pacts import (
    BUILTIN_DEFAULTS,
    EntryStatus,
    FieldKind,
    PartKind,
    TypeRole,
    UrlKind,
)


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
