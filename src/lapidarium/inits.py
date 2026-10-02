"""Composition root: builds the object graph and hands it to the request."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lapidarium.pacts import ServicesProtocol

if TYPE_CHECKING:
    from collections.abc import Callable

    from lapidarium.pacts import RootRequestProtocol


class Services(ServicesProtocol):
    """Flat service namespace, one `cached_property` per service, built per request."""


class ServiceInjectionMiddleware[Response]:
    """Attach `request.services` so views reach mills through protocols only."""

    def __init__(self, get_response: Callable[[RootRequestProtocol], Response]) -> None:
        self.get_response = get_response

    def __call__(self, request: RootRequestProtocol) -> Response:
        request.services = Services()
        return self.get_response(request)
