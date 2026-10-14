from __future__ import annotations

from functools import cached_property
from http import HTTPStatus
from typing import override

import httpx

from lapidarium.pacts import LinkCheckerProtocol

_TIMEOUT = 10.0
# Some hosts refuse HEAD but serve the page; those get a GET.
_NO_HEAD = frozenset({HTTPStatus.METHOD_NOT_ALLOWED, HTTPStatus.FORBIDDEN})


class HttpLinkChecker(LinkCheckerProtocol):
    def __init__(self, *, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    @cached_property
    def _client(self) -> httpx.Client:
        # Built on first use: making a client reads proxy settings, which a
        # page that only lists issues has no need for.
        return httpx.Client(
            timeout=_TIMEOUT, follow_redirects=True, transport=self._transport
        )

    @override
    def is_alive(self, url: str) -> bool:
        try:
            response = self._client.head(url)
        except httpx.HTTPError:
            return False
        if response.status_code in _NO_HEAD:
            try:
                response = self._client.get(url)
            except httpx.HTTPError:
                return False
        return not response.is_error
