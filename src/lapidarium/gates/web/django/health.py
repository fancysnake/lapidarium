from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.cache import never_cache

if TYPE_CHECKING:
    from lapidarium.gates.web.django.rendering import RootRequest


@never_cache
@transaction.non_atomic_requests
def healthz(request: RootRequest) -> HttpResponse:
    """Readiness probe for the container platform: 503 while the database is away."""
    if request.services.database.reachable():
        return HttpResponse("ok", content_type="text/plain")
    return HttpResponse(
        "unavailable", content_type="text/plain", status=HTTPStatus.SERVICE_UNAVAILABLE
    )
