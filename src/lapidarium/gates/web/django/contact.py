from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from lapidarium.gates.web.django.forms import ContactForm
from lapidarium.gates.web.django.rendering import (
    RootRequest,
    refusal,
    render_page,
    sender,
)
from lapidarium.pacts import DeliveryError, RateLimitedError

if TYPE_CHECKING:
    from django.http import HttpResponse

    from lapidarium.pacts import ContactData


# Anonymous, like the newsletter form; see there.
@csrf_exempt
@require_http_methods(["GET", "POST"])
def contact(request: RootRequest) -> HttpResponse:
    outreach = request.services.outreach
    if not outreach.can_contact():
        raise Http404
    form = ContactForm(request.POST or None)
    problem, status = "", HTTPStatus.OK
    if form.is_valid():
        data = form.cleaned_data
        message: ContactData = {
            "name": data["name"],
            "email": data["email"],
            "message": data["message"],
            "trap": data["website"],
        }
        try:
            outreach.contact(message, sender=sender(request))
        except (RateLimitedError, DeliveryError) as exc:
            problem, status = refusal(exc)
        else:
            return HttpResponseRedirect(reverse("contact") + "?sent=1")
    return render_page(
        request,
        "lapidarium/pages/contact.html",
        status=status,
        form=form,
        problem=problem,
        sent="sent" in request.GET,
    )
