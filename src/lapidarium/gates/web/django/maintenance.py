"""While the site is in maintenance, visitors meet one page wherever they go."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from django.conf import settings
from django.shortcuts import render
from django.utils.cache import add_never_cache_headers

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpResponse

    from lapidarium.gates.web.django.rendering import RootRequest


def _exempt(path: str) -> bool:
    """Keep the admin, the health probe and uploads open to everyone."""
    admin = f"/{settings.ADMIN_URL}".rstrip("/")
    return path == admin or path.startswith(
        (f"{admin}/", "/healthz/", settings.MEDIA_URL)
    )


class MaintenanceMiddleware:
    def __init__(self, get_response: Callable[[RootRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: RootRequest) -> HttpResponse:
        if (
            request.user.is_authenticated
            or _exempt(request.path_info)
            or (notice := request.services.site.maintenance()) is None
        ):
            return self.get_response(request)
        response = render(
            request,
            "lapidarium/pages/maintenance.html",
            {"notice": notice},
            status=HTTPStatus.SERVICE_UNAVAILABLE,
        )
        if notice.retry_after is not None:
            response["Retry-After"] = str(notice.retry_after)
        add_never_cache_headers(response)
        return response
