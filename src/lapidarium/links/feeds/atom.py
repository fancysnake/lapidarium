"""Atom feeds: a YouTube channel's uploads, a GitHub repository's releases."""

from __future__ import annotations

import datetime as dt
from functools import cached_property
from typing import TYPE_CHECKING, override
from urllib.parse import urlsplit

import httpx
from defusedxml.ElementTree import ParseError, fromstring

from lapidarium.pacts import DeliveryError, ExternalItemData, FeedSourceProtocol

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

_NS = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}
_TIMEOUT = 15.0


def youtube(channel_id: str) -> tuple[str, str]:
    return (
        "YouTube",
        f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}",
    )


def github(repository: str) -> tuple[str, str]:
    return "GitHub", f"https://github.com/{repository}/releases.atom"


def _text(entry: Element, path: str) -> str:
    found = entry.find(path, _NS)
    return (found.text or "").strip() if found is not None else ""


def _item(source: str, entry: Element) -> ExternalItemData | None:
    if (link := entry.find("atom:link[@rel='alternate']", _NS)) is None:
        link = entry.find("atom:link", _NS)
    when = _text(entry, "atom:published") or _text(entry, "atom:updated")
    external_id = _text(entry, "atom:id")
    if link is None or not when or not external_id:
        return None
    thumbnail = entry.find("media:group/media:thumbnail", _NS)
    return {
        "source": source,
        "external_id": external_id,
        "title": _text(entry, "atom:title"),
        "url": link.get("href", ""),
        "published_at": dt.datetime.fromisoformat(when),
        "thumbnail_url": thumbnail.get("url", "") if thumbnail is not None else "",
    }


def _items(source: str, content: bytes) -> list[ExternalItemData | None]:
    return [_item(source, e) for e in fromstring(content).iterfind("atom:entry", _NS)]


class AtomFeed(FeedSourceProtocol):
    def __init__(
        self, *, source: str, url: str, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._source = source
        self._url = url
        self._transport = transport

    @cached_property
    def _client(self) -> httpx.Client:
        # Built on first use: making a client reads the proxy settings.
        return httpx.Client(
            timeout=_TIMEOUT, follow_redirects=True, transport=self._transport
        )

    @property
    @override
    def name(self) -> str:
        return f"{self._source} {self._url}"

    @override
    def fetch(self) -> list[ExternalItemData]:
        try:
            response = self._client.get(self._url)
        except httpx.HTTPError as exc:
            raise DeliveryError(self.name) from exc
        if response.is_error:
            raise DeliveryError(self.name)
        try:
            items = _items(self._source, response.content)
        except (ParseError, ValueError) as exc:
            raise DeliveryError(self.name) from exc
        return [item for item in items if item]


def any_atom(url: str) -> tuple[str, str]:
    return urlsplit(url).hostname or url, url
