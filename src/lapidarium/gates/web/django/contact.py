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
    attempt,
    render_page,
    sender,
)

if TYPE_CHECKING:
    from django.http import HttpResponse

    from lapidarium.pacts.outreach import ContactData


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
        }
        # A bot told it worked has no reason to try again.
        if not form.caught:
            problem, status = attempt(
                lambda: outreach.contact(message, sender=sender(request))
            )
        if not problem:
            return HttpResponseRedirect(reverse("contact") + "?sent=1")
    return render_page(
        request,
        "lapidarium/pages/contact.html",
        status=status,
        form=form,
        problem=problem,
        sent="sent" in request.GET,
    )
