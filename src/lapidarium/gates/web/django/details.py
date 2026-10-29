from __future__ import annotations

from django.http import Http404, HttpResponse

from lapidarium.gates.web.django.rendering import RootRequest, cached, render_page
from lapidarium.pacts.content import NotFoundError


@cached
def detail(request: RootRequest, *, route: str, slug: str) -> HttpResponse:
    try:
        found = request.services.catalogue.detail(route, slug)
    except NotFoundError as exc:
        raise Http404 from exc
    return render_page(
        request,
        "lapidarium/pages/detail.html",
        detail=found,
        layout=f"lapidarium/layouts/{found.card.entry_type.layout}.html",
    )
