from __future__ import annotations

from typing import TYPE_CHECKING

from lapidarium.gates.web.django.rendering import RootRequest, cached, render_page

if TYPE_CHECKING:
    from django.http import HttpResponse


@cached
def about(request: RootRequest) -> HttpResponse:
    return render_page(
        request,
        "lapidarium/pages/about.html",
        timeline=request.services.catalogue.timeline(),
        can_contact=request.services.outreach.can_contact(),
    )
