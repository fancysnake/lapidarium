"""The unfold sidebar of the admin."""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict

from django.urls import reverse
from django.utils.translation import gettext

from lapidarium.links.db.django.filters import EntryTypeKeyFilter
from lapidarium.links.db.django.models import EntryType

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest


class NavItem(TypedDict):
    title: str
    icon: str
    link: str
    permission: NotRequired[Callable[[HttpRequest], bool]]


class NavGroup(TypedDict):
    title: str
    separator: bool
    items: list[NavItem]


def _can(permission: str) -> Callable[[HttpRequest], bool]:
    return lambda request: request.user.has_perm(f"lapidarium_db.{permission}")


def _item(title: str, *, icon: str, model: str) -> NavItem:
    return {
        "title": title,
        "icon": icon,
        "link": reverse(f"admin:lapidarium_db_{model}_changelist"),
        "permission": _can(f"view_{model}"),
    }


def sidebar_navigation(_request: HttpRequest) -> list[NavGroup]:
    """Unfold sidebar: one item per content type, then the site's own records."""
    entries = reverse("admin:lapidarium_db_entry_changelist")
    content: list[NavItem] = [
        {
            "title": entry_type.label_plural,
            "icon": entry_type.icon or "article",
            "link": f"{entries}?{EntryTypeKeyFilter.parameter_name}={entry_type.key}",
            "permission": _can("view_entry"),
        }
        for entry_type in EntryType.objects.all()
    ]
    return [
        {
            "title": gettext("Content"),
            "separator": False,
            "items": [
                *content,
                _item(gettext("All entries"), icon="list", model="entry"),
            ],
        },
        {
            "title": gettext("Library"),
            "separator": True,
            "items": [
                _item(gettext("Media"), icon="image", model="mediaasset"),
                _item(gettext("Tags"), icon="sell", model="tag"),
                _item(gettext("External items"), icon="rss_feed", model="externalitem"),
            ],
        },
        {
            "title": gettext("Site"),
            "separator": True,
            "items": [
                _item(gettext("Content types"), icon="category", model="entrytype"),
                _item(gettext("Profile"), icon="person", model="profile"),
                _item(gettext("Maintenance"), icon="construction", model="maintenance"),
                _item(gettext("Links"), icon="link", model="link"),
                _item(gettext("Friends"), icon="diversity_3", model="friend"),
                _item(gettext("Showcases"), icon="star", model="showcase"),
                {
                    "title": gettext("Content panel"),
                    "icon": "account_tree",
                    "link": reverse("panel"),
                },
                {
                    "title": gettext("Theme preview"),
                    "icon": "palette",
                    "link": reverse("theme_preview"),
                },
            ],
        },
    ]
