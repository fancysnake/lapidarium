from typing import TYPE_CHECKING

from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse

from lapidarium.gates.web.django.rendering import RootRequest, render_page

if TYPE_CHECKING:
    from django.http import HttpResponse


@staff_member_required
def panel(request: RootRequest) -> HttpResponse:
    return render_page(
        request,
        "lapidarium/pages/panel.html",
        mechanics=request.services.purposes.overview(),
        types_admin=reverse("admin:lapidarium_db_entrytype_changelist"),
    )
