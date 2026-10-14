"""What every public page shares: the typed request, the site frame, the sender."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from django.conf import settings
from django.forms import Form
from django.http import HttpRequest
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from pydantic import BaseModel

from lapidarium.pacts import PAGE_CACHE, DeliveryError, RateLimitedError

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpResponse

    from lapidarium.pacts import ServicesProtocol


# What views hand templates: DTOs, forms and a few plain values.
type PageValue = BaseModel | tuple[BaseModel, ...] | Form | str | bool


class RootRequest(HttpRequest):
    """For typing only; the middleware sets `services` on the real request."""

    services: ServicesProtocol


def render_page(
    request: RootRequest, template: str, *, status: int = 200, **context: PageValue
) -> HttpResponse:
    match = request.resolver_match
    page = {
        "site": request.services.site.chrome(),
        "site_name": settings.SITE_NAME,
        # What the menu marks as the page the visitor is on.
        "current_page": match.url_name if match else "",
        "current_route": match.kwargs.get("route", "") if match else "",
        **context,
    }
    return render(request, template, page, status=status)


def sender(request: HttpRequest) -> str:
    """Who is asking, for rate limits: the client the proxy in front last saw."""
    if forwarded := request.headers.get("x-forwarded-for", ""):
        return forwarded.rsplit(",", 1)[-1].strip()
    return str(request.META.get("REMOTE_ADDR", ""))


def cached[**P](view: Callable[P, HttpResponse]) -> Callable[P, HttpResponse]:
    """Keep the rendered page until content changes or the timeout passes."""
    decorated: Callable[P, HttpResponse] = cache_page(
        settings.PAGE_CACHE_SECONDS, cache=PAGE_CACHE
    )(view)
    return decorated


def refusal(error: RateLimitedError | DeliveryError) -> tuple[str, HTTPStatus]:
    """Return what a form page says about a refused attempt, and its status."""
    if isinstance(error, RateLimitedError):
        return "busy", HTTPStatus.TOO_MANY_REQUESTS
    return "provider", HTTPStatus.BAD_GATEWAY
