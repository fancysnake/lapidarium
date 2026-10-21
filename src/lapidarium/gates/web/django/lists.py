from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import Http404

from lapidarium.gates.web.django.rendering import RootRequest, cached, render_page
from lapidarium.pacts.content import NotFoundError

if TYPE_CHECKING:
    from django.http import HttpResponse


@cached
def listing(request: RootRequest, route: str) -> HttpResponse:
    page = request.GET.get("page", "1")
    if not page.isdigit():
        raise Http404
    filters = {key: str(value) for key, value in request.GET.items() if key != "page"}
    try:
        found = request.services.catalogue.listing(
            route, filters=filters, page=int(page)
        )
    except NotFoundError as exc:
        raise Http404 from exc
    return render_page(request, "lapidarium/pages/list.html", listing=found)
