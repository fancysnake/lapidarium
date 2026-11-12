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


def test_the_new_type_form_needs_the_right_to_add_types(browser):
    browser.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )

    response = browser.post(
        "/admin/panel/new/volunteering/", {**_VOLUNTEERING, "create": "1"}
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert not EntryType.objects.exists()


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
    assert [field.name for field in form.field_labels] == [
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


_SESSION = {
    "label": "Sesja",
    "label_plural": "Sesje",
    "route": "sesje",
    "colour": "#6b3fa0",
    "field_system": "System",
    "field_format": "Format",
    "field_players": "Gracze",
    "new_field_label": "",
    "new_field_kind": "text",
    "allowed_parts": ["text", "video", "image", "audio"],
    "required_parts": ["text"],
    "in_menu": "on",
    "has_detail_page": "on",
    "door_enabled": "on",
}


def test_the_change_form_is_for_staff(site):
    response = site.get("/admin/panel/types/session/")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"].startswith("/admin/login/")


def test_the_change_form_needs_the_right_to_change_types(site):
    site.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )

    response = site.post(
        "/admin/panel/types/session/", {**_SESSION, "label": "Gra", "save": "1"}
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert EntryType.objects.get(key="session").label == "Sesja"


def test_an_unknown_type_has_no_change_form(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.get("/admin/panel/types/saga/")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_the_change_form_opens_on_the_settings_of_the_type(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.get("/admin/panel/types/session/")

    assert response.status_code == HTTPStatus.OK
    assert response.context["entry_type"].key == "session"
    assert response.context["change"] is None
    form = response.context["form"]
    assert {name: form[name].value() for name in form.fields} == {
        "label": "Sesja",
        "label_plural": "Sesje",
        "route": "sesje",
        "colour": "#6b3fa0",
        "allowed_parts": ["text", "video", "image", "audio"],
        "required_parts": ["text"],
        "in_menu": True,
        "has_detail_page": True,
        "door_enabled": True,
        "new_field_label": None,
        "new_field_kind": "text",
        "field_system": "System",
        "field_format": "Format",
        "field_players": "Gracze",
    }
    assert [field.name for field in form.field_labels] == [
        "field_system",
        "field_format",
        "field_players",
    ]
    assert "I agree to these effects" not in response.text


def test_the_panel_links_each_type_to_its_change_form(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.get("/admin/panel/")

    assert 'href="/admin/panel/types/session/"' in response.text
    assert response.context["changed"] is False


def test_a_change_that_affects_no_entry_is_saved_at_once(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.post(
        "/admin/panel/types/session/",
        {
            **_SESSION,
            "label": "Gra",
            "field_players": "Players",
            "new_field_label": "Length in hours",
            "new_field_kind": "number",
            "save": "1",
        },
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"] == "/admin/panel/?changed=1"
    changed = EntryType.objects.get(key="session")
    assert (changed.label, changed.route, changed.layout, changed.list_filters) == (
        "Gra",
        "sesje",
        "media_first",
        ["year", "tag", "system", "format"],
    )
    assert list(changed.fields.values_list("key", "label", "kind")) == [
        ("system", "System", "text"),
        ("format", "Format", "choice"),
        ("players", "Players", "text"),
        ("length_in_hours", "Length in hours", "number"),
    ]
    panel = site.get(response["Location"])
    assert panel.context["changed"] is True
    assert "The type is changed." in panel.text


def test_preview_lists_what_a_change_does_to_entries_without_saving(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.post(
        "/admin/panel/types/session/",
        {
            **_SESSION,
            "route": "sessions",
            "allowed_parts": ["text", "image", "audio"],
            "required_parts": ["text", "image"],
            "preview": "1",
        },
    )

    assert response.status_code == HTTPStatus.OK
    change = response.context["change"]
    assert [(e.kind, e.entries, e.part) for e in change.effects] == [
        ("moved", 2, None),
        ("part_refused", 1, "video"),
        ("part_missing", 2, "image"),
    ]
    assert change.saved is False
    assert response.context["form"].errors == {}
    assert "2 entries move to a new address" in response.text
    assert (
        "1 entry holds a video part and cannot be saved until the part is removed"
        in response.text
    )
    assert (
        "2 entries have no image part and cannot be saved until they get one"
        in response.text
    )
    assert f'name="agree" value="{change.consent}"' in response.text
    assert EntryType.objects.get(key="session").route == "sesje"


def test_save_waits_for_consent_to_the_effects_shown(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))
    moved = {**_SESSION, "route": "sessions", "save": "1"}

    asked = site.post("/admin/panel/types/session/", moved)

    assert asked.status_code == HTTPStatus.OK
    assert asked.context["change"].consent == "moved::2"
    assert "2 entries move to a new address" in asked.text
    assert EntryType.objects.get(key="session").route == "sesje"

    stale = site.post("/admin/panel/types/session/", {**moved, "agree": "moved::1"})

    assert stale.status_code == HTTPStatus.OK
    assert EntryType.objects.get(key="session").route == "sesje"

    agreed = site.post("/admin/panel/types/session/", {**moved, "agree": "moved::2"})

    assert agreed.status_code == HTTPStatus.FOUND
    assert agreed["Location"] == "/admin/panel/?changed=1"
    assert EntryType.objects.get(key="session").route == "sessions"


def test_pages_lost_are_counted(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))
    data = {k: v for k, v in _SESSION.items() if k != "has_detail_page"}

    lost = site.post("/admin/panel/types/session/", {**data, "preview": "1"})

    assert [(e.kind, e.entries) for e in lost.context["change"].effects] == [
        ("page_lost", 2)
    ]
    assert "2 entries lose their own pages" in lost.text


def test_pages_gained_are_counted(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))
    EntryType.objects.filter(key="session").update(has_detail_page=False)

    gained = site.post("/admin/panel/types/session/", {**_SESSION, "preview": "1"})

    assert [(e.kind, e.entries) for e in gained.context["change"].effects] == [
        ("page_gained", 2)
    ]
    assert "2 entries get their own pages" in gained.text


def test_change_refuses_what_the_rules_forbid_and_keeps_the_form(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.post(
        "/admin/panel/types/session/",
        {**_SESSION, "route": "about", "new_field_label": "System", "save": "1"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["change"] is None
    assert response.context["form"].errors == {
        "__all__": [
            "/about/ belongs to the about page.",
            "A field with the key 'system' already exists.",
        ]
    }
    assert EntryType.objects.get(key="session").route == "sesje"


def test_change_asks_again_for_what_the_form_cannot_read(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.post(
        "/admin/panel/types/session/",
        {**_SESSION, "field_system": "", "new_field_kind": "relation", "save": "1"},
    )

    assert response.status_code == HTTPStatus.OK
    assert set(response.context["form"].errors) == {"field_system", "new_field_kind"}
    assert EntryType.objects.get(key="session").label == "Sesja"
