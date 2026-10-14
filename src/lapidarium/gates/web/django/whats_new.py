from __future__ import annotations

from typing import TYPE_CHECKING

from lapidarium.gates.web.django.rendering import RootRequest, cached, render_page

if TYPE_CHECKING:
    from django.http import HttpResponse


@cached
def whats_new(request: RootRequest) -> HttpResponse:
    return render_page(
        request,
        "lapidarium/pages/whats_new.html",
        items=request.services.catalogue.whats_new(),
    )
