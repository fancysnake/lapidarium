from __future__ import annotations

from typing import TYPE_CHECKING

from lapidarium.gates.web.django.rendering import RootRequest, render_page

if TYPE_CHECKING:
    from django.http import HttpResponse


def search(request: RootRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    return render_page(
        request,
        "lapidarium/pages/search.html",
        query=query,
        results=request.services.catalogue.search(query),
    )
