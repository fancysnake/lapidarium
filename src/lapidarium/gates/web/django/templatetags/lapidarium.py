from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

import markdown as markdown_lib
import nh3
from django import template
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import SafeString

from lapidarium.gates.web.django import embeds
from lapidarium.gates.web.django.paths import entry_path
from lapidarium.pacts import BUTTON_SIZE

if TYPE_CHECKING:
    from collections.abc import Mapping

    from django.template.context import Context

    from lapidarium.pacts import EntryDTO, EntryRefDTO

register = template.Library()


@register.simple_tag(takes_context=True)
def entry_url(context: Context, entry: EntryDTO | EntryRefDTO) -> str:
    return entry_path(context["site"].types, type_key=entry.type_key, slug=entry.slug)


@register.simple_tag(takes_context=True)
def absolute(context: Context, path: str) -> str:
    return str(context["request"].build_absolute_uri(path))


@register.simple_tag(takes_context=True)
def link_back(context: Context) -> SafeString:
    """Build the HTML that links here: the site's button, else its owner's name."""
    site = context["site"]
    home = absolute(context, reverse("home"))
    if site.profile and site.profile.button:
        width, height = BUTTON_SIZE
        return format_html(
            '<a href="{}"><img src="{}" width="{}" height="{}" alt="{}"></a>',
            home,
            absolute(context, site.profile.button.url),
            width,
            height,
            site.owner_name,
        )
    return format_html('<a href="{}">{}</a>', home, site.owner_name)


@register.filter
def markdown(text: str) -> SafeString:
    """Render markdown and keep only what nh3 lets through."""
    return SafeString(nh3.clean(markdown_lib.markdown(text)))


@register.filter
def video_embed(url: str) -> str:
    return embeds.video_embed(url)


@register.filter
def file_name(path: str) -> str:
    return PurePosixPath(path).name


@register.filter
def file_kind(path: str) -> str:
    return PurePosixPath(path).suffix.removeprefix(".").upper()


@register.filter
def host(url: str) -> str:
    return (urlsplit(url).hostname or "").removeprefix("www.")


@register.filter
def option(options: Mapping[str, str], key: str) -> str:
    return options.get(key, "")
