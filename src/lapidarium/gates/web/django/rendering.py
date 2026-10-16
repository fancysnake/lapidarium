"""What every public page shares: the typed request, the site frame, the sender."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from django.conf import settings
from django.forms import Form
from django.http import HttpRequest
from django.shortcuts import render
from django.utils.translation import gettext as _
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
    """Who is asking, for rate limits: the client the outermost trusted proxy saw.

    Each trusted proxy appends the address it was reached from, so the entry
    `TRUSTED_PROXY_HOPS` from the end is the first one a client cannot forge.
    """
    hops: int = settings.TRUSTED_PROXY_HOPS
    header = request.headers.get("x-forwarded-for", "")
    forwarded = [hop for part in header.split(",") if (hop := part.strip())]
    if hops and len(forwarded) >= hops:
        return forwarded[-hops]
    return str(request.META.get("REMOTE_ADDR", ""))


def cached[**P](view: Callable[P, HttpResponse]) -> Callable[P, HttpResponse]:
    """Keep the rendered page until content changes or the timeout passes."""
    decorated: Callable[P, HttpResponse] = cache_page(
        settings.PAGE_CACHE_SECONDS, cache=PAGE_CACHE
    )(view)
    return decorated


def attempt(send: Callable[[], None]) -> tuple[str, HTTPStatus]:
    """Run `send`; return what a form page says if it is refused, and the status."""
    try:
        send()
    except RateLimitedError:
        return (
            _(
                "That was a lot of tries in a short time. "
                "Please wait a while and try again."
            ),
            HTTPStatus.TOO_MANY_REQUESTS,
        )
    except DeliveryError:
        return (
            _("Something went wrong on the way. Please try again later."),
            HTTPStatus.BAD_GATEWAY,
        )
    return "", HTTPStatus.OK
