from typing import TYPE_CHECKING

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from lapidarium.gates.web.django.forms import ChangeTypeForm, NewTypeForm
from lapidarium.gates.web.django.rendering import RootRequest, render_page
from lapidarium.pacts.content import NotFoundError
from lapidarium.pacts.purposes import (
    ConsentNeededError,
    FieldsInUseError,
    TypeValidationError,
)

if TYPE_CHECKING:
    from django.forms import Form
    from django.http import HttpResponse

    from lapidarium.pacts.content import EntryTypeDTO
    from lapidarium.pacts.purposes import FieldUseDTO, TypeChangeData, TypeChangeDTO


def _add_errors(form: Form, error: TypeValidationError) -> None:
    for message in error.messages:
        form.add_error(None, message)


@staff_member_required
def panel(request: RootRequest) -> HttpResponse:
    mechanics = request.services.purposes.overview()
    types = (use.entry_type for mechanic in mechanics for use in mechanic.types)
    return render_page(
        request,
        "lapidarium/pages/panel.html",
        mechanics=mechanics,
        types_admin=reverse("admin:lapidarium_db_entrytype_changelist"),
        entries_admin=reverse("admin:lapidarium_db_entry_changelist"),
        entry_add=reverse("admin:lapidarium_db_entry_add"),
        created=next((t for t in types if t.key == request.GET.get("created")), None),
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
            _add_errors(form, exc)
        else:
            if creating:
                return HttpResponseRedirect(f"{reverse('panel')}?created={preview.key}")
    return render_page(
        request,
        "lapidarium/pages/panel_new.html",
        purpose=chosen,
        form=form,
        preview=preview,
    )


def _save_or_plan(
    request: RootRequest, key: str, *, data: TypeChangeData
) -> TypeChangeDTO | None:
    """Save the change on "Save" and return `None`; else return its preview."""
    changes = request.services.type_changes
    if "save" in request.POST:
        changes.change(key, data, consent=request.POST.get("agree", ""))
        return None
    return changes.plan_change(key, data)


@staff_member_required
@permission_required("lapidarium_db.change_entrytype", raise_exception=True)
@require_http_methods(["GET", "POST"])
def panel_change(request: RootRequest, key: str) -> HttpResponse:
    """One form: "Preview" shows the change, "Save" needs consent to its effects."""
    try:
        entry_type = request.services.type_changes.entry_type(key)
    except NotFoundError as exc:
        raise Http404 from exc
    form = ChangeTypeForm(request.POST or None, entry_type=entry_type)
    change: TypeChangeDTO | None = None
    in_use: tuple[FieldUseDTO, ...] = ()
    if form.is_valid():
        try:
            change = _save_or_plan(request, key, data=form.to_data())
        except ConsentNeededError as exc:
            change = exc.change
        except TypeValidationError as exc:
            _add_errors(form, exc)
        except FieldsInUseError as exc:
            in_use = exc.uses
        else:
            if change is None:
                return HttpResponseRedirect(reverse("panel") + "?changed=1")
    return render_page(
        request,
        "lapidarium/pages/panel_change.html",
        entry_type=entry_type,
        form=form,
        change=change,
        in_use=in_use,
    )


@staff_member_required
@permission_required("lapidarium_db.view_entry", raise_exception=True)
def panel_field(request: RootRequest, key: str, *, field: str) -> HttpResponse:
    """List the entries that keep a field from removal or a change of kind."""
    try:
        use = request.services.type_changes.field_use(key, field)
    except NotFoundError as exc:
        raise Http404 from exc
    return render_page(
        request,
        "lapidarium/pages/panel_field.html",
        type_key=key,
        use=use,
        entries_admin=reverse("admin:lapidarium_db_entry_changelist"),
    )
