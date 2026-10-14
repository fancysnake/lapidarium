from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils.translation import gettext as _

if TYPE_CHECKING:
    from django.http import HttpResponse

    from lapidarium.gates.web.django.rendering import RootRequest


@staff_member_required
def content_health(request: RootRequest) -> HttpResponse:
    """Show the admin what `check_content` lists, without visiting links."""
    return render(
        request,
        "admin/lapidarium/content_health.html",
        {
            **admin.site.each_context(request),
            "title": _("Content health"),
            "issues": request.services.content_health.check(links=False),
        },
    )
