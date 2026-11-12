from typing import TYPE_CHECKING

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from lapidarium.gates.web.django.forms import ChangeTypeForm, NewTypeForm
from lapidarium.gates.web.django.rendering import RootRequest, render_page
from lapidarium.pacts.content import NotFoundError
from lapidarium.pacts.purposes import TypeValidationError

if TYPE_CHECKING:
    from django.http import HttpResponse

    from lapidarium.pacts.content import EntryTypeDTO
    from lapidarium.pacts.purposes import TypeChangeDTO


@staff_member_required
def panel(request: RootRequest) -> HttpResponse:
    return render_page(
        request,
        "lapidarium/pages/panel.html",
        mechanics=request.services.purposes.overview(),
        types_admin=reverse("admin:lapidarium_db_entrytype_changelist"),
        created="created" in request.GET,
        changed="changed" in request.GET,
    )


@staff_member_required
@permission_required("lapidarium_db.add_entrytype", raise_exception=True)
@require_http_methods(["GET", "POST"])
def panel_new(request: RootRequest, purpose: str) -> HttpResponse:
    """One form: "Preview" shows the type it would make, "Create" saves it."""
    purposes = request.services.purposes
    try:
        chosen = purposes.purpose(purpose)
    except NotFoundError as exc:
        raise Http404 from exc
    form = NewTypeForm(request.POST or None, purpose=chosen)
    preview: EntryTypeDTO | None = None
    if form.is_valid():
        creating = "create" in request.POST
        act = purposes.create if creating else purposes.plan
        try:
            preview = act(purpose, form.to_data())
        except TypeValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
        else:
            if creating:
                return HttpResponseRedirect(reverse("panel") + "?created=1")
    return render_page(
        request,
        "lapidarium/pages/panel_new.html",
        purpose=chosen,
        form=form,
        preview=preview,
    )


@staff_member_required
@permission_required("lapidarium_db.change_entrytype", raise_exception=True)
@require_http_methods(["GET", "POST"])
def panel_change(request: RootRequest, key: str) -> HttpResponse:
    """One form: "Preview" shows the change, "Save" needs consent to its effects."""
    purposes = request.services.purposes
    try:
        entry_type = purposes.entry_type(key)
    except NotFoundError as exc:
        raise Http404 from exc
    form = ChangeTypeForm(request.POST or None, entry_type=entry_type)
    change: TypeChangeDTO | None = None
    if form.is_valid():
        data = form.to_data()
        consent = request.POST.get("agree", "")
        try:
            change = (
                purposes.change(key, data, consent=consent)
                if "save" in request.POST
                else purposes.plan_change(key, data)
            )
        except TypeValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
        else:
            if change.saved:
                return HttpResponseRedirect(reverse("panel") + "?changed=1")
    return render_page(
        request,
        "lapidarium/pages/panel_change.html",
        entry_type=entry_type,
        form=form,
        change=change,
    )
