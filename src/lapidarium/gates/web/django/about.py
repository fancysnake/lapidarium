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
        about=request.services.site.about(),
        can_contact=request.services.outreach.can_contact(),
    )
