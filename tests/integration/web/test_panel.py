"""The content panel: staff see the site's types grouped by what they are for."""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model

from lapidarium.links.db.django.models import EntryType

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


def test_the_panel_is_for_staff(site):
    response = site.get("/admin/panel/")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"].startswith("/admin/login/")


def test_the_panel_groups_the_demo_types_by_purpose(site):
    site.force_login(
        get_user_model().objects.create_superuser("curator", password="pw")
    )

    response = site.get("/admin/panel/")

    assert response.status_code == HTTPStatus.OK
    assert response.context["types_admin"] == "/admin/lapidarium_db/entrytype/"
    assert {
        mechanic.name: [
            (
                use.entry_type.key,
                use.entries,
                [t.key for t in use.containers],
                [t.key for t in use.contents],
            )
            for use in mechanic.types
        ]
        for mechanic in response.context["mechanics"]
    } == {
        "Pieces of work": [
            ("session", 2, ["project"], []),
            ("song", 1, [], []),
            ("game", 1, [], []),
            ("meme", 1, [], []),
            ("article", 1, ["wiki_section"], []),
        ],
        "Events": [("event", 3, [], [])],
        "Projects": [("project", 2, ["initiative"], ["session"])],
        "Activities": [("initiative", 1, [], ["project"])],
        "Sections": [("wiki_section", 1, [], ["article"])],
    }
    assert "/admin/lapidarium_db/entrytype/?key=song" in response.text
    assert "Paid work for an employer" in response.text


def test_the_admin_link_of_a_type_lists_that_type_only(admin):
    for key in ("song", "songbook"):
        EntryType.objects.create(key=key, label=key, route=key)

    response = admin.get("/admin/lapidarium_db/entrytype/?key=song")

    assert response.status_code == HTTPStatus.OK
    assert [t.key for t in response.context["cl"].result_list] == ["song"]


def test_the_panel_of_an_empty_site_names_every_purpose(browser):
    browser.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = browser.get("/admin/panel/")

    assert response.status_code == HTTPStatus.OK
    assert [(m.name, m.types) for m in response.context["mechanics"]] == [
        ("Pieces of work", ()),
        ("Events", ()),
        ("Projects", ()),
        ("Activities", ()),
        ("Sections", ()),
    ]
    assert response.text.count("No types yet.") == 5


def test_the_panel_names_purposes_in_polish(browser):
    browser.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = browser.get("/admin/panel/", HTTP_ACCEPT_LANGUAGE="pl")

    assert '<h2 class="section-title" id="mechanic-thing">Prace</h2>' in response.text
    assert (
        '<strong><a href="/admin/panel/new/volunteering/">Wolontariat</a></strong>:'
        " Nieodpłatna praca"
    ) in response.text
    assert "Nie ma jeszcze rodzajów." in response.text


_VOLUNTEERING = {
    "label": "Volunteering",
    "label_plural": "Volunteering",
    "route": "volunteering",
    "colour": "#6b3fa0",
    "field_organisation": "Organisation",
    "field_position": "",
    "key": "",
    "allowed_parts": ["text", "image"],
    "in_menu": "on",
    "has_detail_page": "on",
}


def test_the_new_type_form_is_for_staff(browser):
    response = browser.get("/admin/panel/new/volunteering/")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"].startswith("/admin/login/")


def test_the_new_type_form_opens_on_what_the_purpose_suggests(browser):
    browser.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = browser.get("/admin/panel/new/volunteering/")

    assert response.status_code == HTTPStatus.OK
    assert response.context["purpose"].key == "volunteering"
    assert response.context["preview"] is None
    form = response.context["form"]
    assert {name: form[name].value() for name in form.fields} == {
        "label": "Volunteering",
        "label_plural": "Volunteering",
        "route": "volunteering",
        "colour": "#000000",
        "key": None,
        "allowed_parts": ["text", "video", "audio", "image", "file", "link"],
        "required_parts": None,
        "in_menu": True,
        "has_detail_page": True,
        "door_enabled": False,
        "field_organisation": "Organisation",
        "field_position": "Position",
    }
    assert [field.name for field in form.starters] == [
        "field_organisation",
        "field_position",
    ]


def test_an_unknown_purpose_has_no_form(browser):
    browser.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = browser.get("/admin/panel/new/hobby/")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_preview_shows_the_type_without_saving_it(browser):
    browser.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = browser.post(
        "/admin/panel/new/volunteering/", {**_VOLUNTEERING, "preview": "1"}
    )

    assert response.status_code == HTTPStatus.OK
    preview = response.context["preview"]
    assert (preview.key, preview.role, preview.route) == (
        "volunteering",
        "container_timespan",
        "volunteering",
    )
    assert [f.label for f in preview.fields] == ["Organisation"]
    assert "A list of Volunteering at /volunteering/" in response.text
    assert response.context["form"].errors == {}
    assert not EntryType.objects.exists()


def test_create_saves_the_type_and_returns_to_the_panel(browser):
    browser.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = browser.post(
        "/admin/panel/new/volunteering/", {**_VOLUNTEERING, "create": "1"}
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"] == "/admin/panel/?created=1"
    created = EntryType.objects.get()
    assert (
        created.key,
        created.label,
        created.route,
        created.role,
        created.colour,
        created.allowed_parts,
        created.required_parts,
        created.in_menu,
        created.has_detail_page,
        created.door_enabled,
    ) == (
        "volunteering",
        "Volunteering",
        "volunteering",
        "container_timespan",
        "#6b3fa0",
        ["text", "image"],
        [],
        True,
        True,
        False,
    )
    assert list(created.fields.values_list("key", "label", "kind")) == [
        ("organisation", "Organisation", "text")
    ]
    panel = browser.get(response["Location"])
    assert panel.context["created"] is True
    assert "The type is created." in panel.text
    assert [
        [use.entry_type.key for use in mechanic.types]
        for mechanic in panel.context["mechanics"]
        if mechanic.name == "Activities"
    ] == [["volunteering"]]


def test_create_refuses_what_the_rules_forbid_and_keeps_the_form(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.post(
        "/admin/panel/new/volunteering/",
        {**_VOLUNTEERING, "key": "song", "route": "about", "create": "1"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["preview"] is None
    assert response.context["form"].errors == {
        "__all__": [
            "/about/ belongs to the about page.",
            "A type with the key 'song' already exists.",
        ]
    }
    assert not EntryType.objects.filter(route="about").exists()


def test_create_asks_again_for_what_the_form_cannot_read(browser):
    browser.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = browser.post(
        "/admin/panel/new/volunteering/",
        {**_VOLUNTEERING, "route": "two words", "colour": "purple", "create": "1"},
    )

    assert response.status_code == HTTPStatus.OK
    assert set(response.context["form"].errors) == {"route", "colour"}
    assert not EntryType.objects.exists()
