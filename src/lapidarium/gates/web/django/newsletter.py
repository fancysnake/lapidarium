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
    refusal,
    render_page,
    sender,
)
from lapidarium.pacts import DeliveryError, RateLimitedError

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
        try:
            request.services.outreach.subscribe(
                form.cleaned_data["email"],
                trap=form.cleaned_data["website"],
                sender=sender(request),
            )
        except (RateLimitedError, DeliveryError) as exc:
            problem, status = refusal(exc)
        else:
            return HttpResponseRedirect(reverse("newsletter") + "?subscribed=1")
    return render_page(
        request,
        "lapidarium/pages/newsletter.html",
        status=status,
        form=form,
        problem=problem,
        subscribed="subscribed" in request.GET,
    )
