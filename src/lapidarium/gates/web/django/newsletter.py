from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from lapidarium.gates.web.django.forms import NewsletterForm
from lapidarium.gates.web.django.rendering import (
    RootRequest,
    attempt,
    render_page,
    sender,
)

if TYPE_CHECKING:
    from django.http import HttpResponse


# Anonymous and harmless to forge: a forged request does nothing the attacker
# could not do directly. Exempt, so cached pages need no per-visitor token.
@csrf_exempt
@require_http_methods(["GET", "POST"])
def newsletter(request: RootRequest) -> HttpResponse:
    form = NewsletterForm(request.POST or None)
    problem, status = "", HTTPStatus.OK
    if form.is_valid():
        email = form.cleaned_data["email"]
        # A bot told it worked has no reason to try again.
        if not form.caught:
            problem, status = attempt(
                lambda: request.services.outreach.subscribe(
                    email, sender=sender(request)
                )
            )
        if not problem:
            return HttpResponseRedirect(reverse("newsletter") + "?subscribed=1")
    return render_page(
        request,
        "lapidarium/pages/newsletter.html",
        status=status,
        form=form,
        problem=problem,
        subscribed="subscribed" in request.GET,
    )
