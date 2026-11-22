"""Admin for content types: the shared type check, derived colours, the role lock."""

from http import HTTPStatus

import pytest

from lapidarium import inits
from lapidarium.links.db.django.models import EntryType
from tests.factories import admin_errors, admin_inline

TYPES = "/admin/lapidarium_db/entrytype/"

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


def _type(**values):
    return {
        "label": "Talk",
        "label_plural": "Talks",
        "key": "talk",
        "route": "talks",
        "order": "0",
        "role": "thing",
        "colour": "#6b3fa0",
        "tint": "",
        "icon": "",
        "allowed_parts": ["text"],
        "door_pick": "latest",
        "door_min_entries": "1",
        **values,
        **admin_inline("fields", values.pop("fields", ())),
    }


def _field(key, kind, **values):
    return {
        "key": key,
        "label": key.title(),
        "kind": kind,
        "choices": "",
        "url_kind": "any",
        "target_type": "",
        "order": "0",
        **values,
    }


def test_type_gets_a_derived_tint_and_its_fields(admin):
    response = admin.post(
        f"{TYPES}add/",
        _type(
            required_parts=["text"],
            fields=[
                _field("event", "text"),
                _field("format", "choice", choices="talk, workshop"),
            ],
        ),
    )

    assert response.status_code == HTTPStatus.FOUND
    talk = EntryType.objects.get(key="talk")
    assert talk.tint == "#ede8f4"
    assert talk.allowed_parts == ["text"]
    assert list(talk.fields.values_list("key", "choices")) == [
        ("event", []),
        ("format", ["talk", "workshop"]),
    ]


def test_type_refuses_low_contrast_and_unallowed_required_parts(admin):
    response = admin.post(
        f"{TYPES}add/",
        _type(
            colour="#999999",
            required_parts=["video"],
            fields=[_field("format", "choice"), _field("inspired_by", "relation")],
        ),
    )

    form_errors, inlines = admin_errors(response)
    assert form_errors == {
        "colour": [
            "Contrast with the page background is 2.85:1, needs 4.5:1.",
            "Contrast with the tint is 2.57:1, needs 4.5:1.",
        ],
        "required_parts": ["Required parts must be allowed."],
    }
    assert inlines["fields"] == (
        [
            {"choices": ["A choice field needs choices."]},
            {"target_type": ["A relation field needs a target type."]},
        ],
        [],
    )


def test_type_errors_from_the_shared_check_are_translated(admin):
    response = admin.post(
        f"{TYPES}add/", _type(required_parts=["video"]), HTTP_ACCEPT_LANGUAGE="pl"
    )

    form_errors, _ = admin_errors(response)
    assert form_errors == {"required_parts": ["Wymagane części muszą być dozwolone."]}


@pytest.mark.usefixtures("demo")
def test_type_refuses_a_list_filter_on_a_field_removed_in_the_same_save(admin):
    session = EntryType.objects.get(key="session")
    rows = [
        {
            **_field(field.key, field.kind, choices=", ".join(field.choices)),
            "label": field.label,
            "id": field.pk,
            "entry_type": session.pk,
            **({"DELETE": "on"} if field.key == "format" else {}),
        }
        for field in session.fields.all()
    ]
    data = _type(
        key="session", route=session.route, list_filters=["year", "format"], fields=rows
    )
    data["fields-INITIAL_FORMS"] = str(len(rows))

    response = admin.post(f"{TYPES}{session.pk}/change/", data)

    form_errors, inlines = admin_errors(response)
    assert not form_errors
    assert inlines["fields"] == (
        [],
        ["List filter 'format' is neither year, tag nor one of the fields."],
    )
    assert session.fields.filter(key="format").exists()


@pytest.mark.usefixtures("demo")
def test_type_change_offers_its_own_fields_as_list_filters(admin):
    session = EntryType.objects.get(key="session")

    response = admin.get(f"{TYPES}{session.pk}/change/")

    form = response.context["adminform"].form
    assert form.fields["list_filters"].choices == [
        ("year", "Year"),
        ("tag", "Tag"),
        ("system", "System"),
        ("format", "Format"),
        ("players", "Gracze"),
    ]
    assert form.initial["list_filters"] == ["year", "tag", "system", "format"]


def _talk():
    return EntryType.objects.create(
        key="talk", label="Talk", label_plural="Talks", route="t", colour="#6b3fa0"
    )


def test_type_change_has_no_dark_colour_without_a_dark_scheme(admin):
    response = admin.get(f"{TYPES}{_talk().pk}/change/")

    field = _readonly(response, "dark_colour")
    assert field.contents() == "—"


def test_type_change_shows_the_derived_dark_colour(
    *, admin, settings, monkeypatch, layered_theme
):
    settings.THEME_STATIC_DIRS = (
        ("themes/base", settings.ENGINE_THEMES / "base"),
        ("themes/dusk", layered_theme),
    )
    monkeypatch.setattr(inits, "PROCESS", inits.Process())

    response = admin.get(f"{TYPES}{_talk().pk}/change/")

    field = _readonly(response, "dark_colour")
    assert "#997bbd" in field.contents()


def _readonly(response, name):
    return next(
        field
        for fieldset in response.context["adminform"]
        for line in fieldset
        for field in line
        if field.is_readonly and field.field["name"] == name
    )


@pytest.mark.usefixtures("demo")
def test_type_with_entries_keeps_its_role(admin):
    event = EntryType.objects.get(key="event")
    url = f"{TYPES}{event.pk}/change/"

    page = admin.get(url)
    response = admin.post(
        url, _type(label="Event", key="event", route=event.route, role="thing")
    )

    assert "role" not in page.context["adminform"].form.fields
    assert "role is fixed once it has entries." in page.content.decode()
    assert response.status_code == HTTPStatus.FOUND
    event.refresh_from_db()
    assert (event.label, event.role) == ("Event", "calendar")


def test_type_without_entries_changes_its_role(admin):
    admin.post(f"{TYPES}add/", _type())
    talk = EntryType.objects.get(key="talk")

    response = admin.post(f"{TYPES}{talk.pk}/change/", _type(role="calendar"))

    assert response.status_code == HTTPStatus.FOUND
    talk.refresh_from_db()
    assert talk.role == "calendar"


@pytest.mark.parametrize(
    "case",
    (
        ("about", "/about/ belongs to the about page."),
        ("admin", "/admin/ belongs to the admin."),
        ("static", "/static/ belongs to static files."),
    ),
)
def test_type_refuses_a_route_already_taken(admin, case):
    route, error = case
    response = admin.post(f"{TYPES}add/", _type(route=route))

    form_errors, _ = admin_errors(response)
    assert form_errors == {"route": [error]}
    assert not EntryType.objects.filter(key="talk").exists()


def test_type_list_flags_types_on_a_taken_route(admin):
    EntryType.objects.create(
        key="find", label="Find", label_plural="Finds", route="search"
    )
    EntryType.objects.create(
        key="talk", label="Talk", label_plural="Talks", route="talks"
    )

    content = admin.get(TYPES).content.decode()

    assert content.count("<strong>⚠") == 1
    assert "search <strong>⚠ /search/ belongs to the search page.</strong>" in content


def test_type_refuses_a_malformed_colour(admin):
    response = admin.post(f"{TYPES}add/", _type(colour="red"))

    form_errors, _ = admin_errors(response)
    assert form_errors == {"colour": ["Use #rrggbb."]}
