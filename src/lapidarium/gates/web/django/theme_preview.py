from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.admin.views.decorators import staff_member_required

from lapidarium.gates.web.django.forms import ContactForm
from lapidarium.gates.web.django.rendering import RootRequest, render_page

if TYPE_CHECKING:
    from django.http import HttpResponse


@staff_member_required
def theme_preview(request: RootRequest) -> HttpResponse:
    """Every component on the site's own content: the theme's test page and docs."""
    return render_page(
        request,
        "lapidarium/pages/theme_preview.html",
        home=request.services.catalogue.home(),
        theme=request.services.theme.active(),
        problems=tuple(request.services.theme.check()),
        form=ContactForm(),
    )
