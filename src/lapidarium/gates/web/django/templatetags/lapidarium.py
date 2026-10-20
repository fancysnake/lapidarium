from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

import markdown as markdown_lib
import nh3
from django import template
from django.utils.safestring import SafeString

from lapidarium.gates.web.django import embeds
from lapidarium.gates.web.django.paths import entry_path

if TYPE_CHECKING:
    from collections.abc import Mapping

    from django.template.context import Context

    from lapidarium.pacts.content import EntryDTO, EntryRefDTO
    from lapidarium.pacts.health import HealthIssueDTO

register = template.Library()


@register.simple_tag(takes_context=True)
def entry_url(context: Context, entry: EntryDTO | EntryRefDTO) -> str:
    return entry_path(context["site"].types, type_key=entry.type_key, slug=entry.slug)


@register.simple_tag(takes_context=True)
def absolute(context: Context, path: str) -> str:
    return str(context["request"].build_absolute_uri(path))


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


@register.simple_tag(takes_context=True)
def content_health(context: Context) -> list[HealthIssueDTO]:
    """Return the issues the admin dashboard lists; it has no view of its own."""
    issues: list[HealthIssueDTO] = context["request"].services.content_health.check(
        links=False
    )
    return issues
