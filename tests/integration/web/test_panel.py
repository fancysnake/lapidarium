"""The content panel: staff see the site's types grouped by what they are for."""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model

from lapidarium.links.db.django.models import Entry, EntryType, Profile
from lapidarium.specs import DESK_RECENT

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


def test_the_panel_is_for_staff(site):
    response = site.get("/panel/structure/")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"].startswith("/admin/login/")


def test_the_panel_drops_the_menu_and_the_footer_of_the_site(site):
    site.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )

    response = site.get("/panel/structure/")

    assert "site-footer" not in response.text
    assert 'aria-label="Main menu"' not in response.text
    assert '<a href="/">View the site</a>' in response.text


def test_the_desk_is_for_staff(site):
    response = site.get("/panel/")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"].startswith("/admin/login/")


def test_the_desk_offers_every_type_and_lists_drafts_and_what_is_coming(site):
    Entry.objects.filter(slug="bal-w-zamku").update(status="draft")
    site.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )

    response = site.get("/panel/")

    assert response.status_code == HTTPStatus.OK
    desk = response.context["desk"]
    assert [row.entry.slug for row in desk.drafts] == ["bal-w-zamku"]
    assert desk.total == Entry.objects.count()
    assert len(desk.published) == DESK_RECENT
    assert all(row.entry.status == "published" for row in desk.published)
    assert [card.entry_type.key for card in response.context["upcoming"]] == [
        "event"
    ] * len(response.context["upcoming"])
    assert 'href="/admin/lapidarium_db/entry/add/?type=song">Piosenka</a>' in (
        response.text
    )
    assert (
        'href="/admin/lapidarium_db/entry/?type=session&amp;q=bal-w-zamku">'
        "Bal w zamku Ravenloft</a>"
    ) in response.text
    assert 'aria-current="page">Desk</a>' in response.text
    assert "helper" in response.text


def test_the_desk_of_an_empty_site_points_to_structure(browser):
    browser.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = browser.get("/panel/")

    assert response.status_code == HTTPStatus.OK
    assert response.context["desk"].total == 0
    assert '<a href="/panel/structure/">Add a type in Structure</a>' in response.text
    assert "No drafts." in response.text
    assert "Nothing is published yet." in response.text
    assert "No event is planned." in response.text


def test_the_entries_are_for_staff(site):
    response = site.get("/panel/entries/")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"].startswith("/admin/login/")


def test_the_entries_list_every_entry_with_its_container(site):
    Entry.objects.filter(slug="bal-w-zamku").update(status="draft")
    site.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )

    response = site.get("/panel/entries/")

    assert response.status_code == HTTPStatus.OK
    entries = response.context["entries"]
    total = Entry.objects.count()
    assert (entries.total, entries.drafts, entries.published) == (total, 1, total - 1)
    assert (entries.page, entries.pages, len(entries.rows)) == (1, 1, total)
    assert (entries.entry_type, entries.status, entries.query) == (None, None, "")
    assert {count.entry_type.key: count.entries for count in entries.types}[
        "session"
    ] == 2
    row = next(row for row in entries.rows if row.entry.slug == "bal-w-zamku")
    assert [container.type_key for container in row.containers] == ["project"]
    assert (
        'href="/admin/lapidarium_db/entry/?type=session&amp;q=bal-w-zamku">'
        "Bal w zamku Ravenloft</a>"
    ) in response.text
    assert "1 draft is not on the site yet." in response.text
    assert 'aria-current="page">All entries</a>' in response.text


def test_the_entries_filter_by_type_status_and_title(site):
    Entry.objects.filter(slug="bal-w-zamku").update(status="draft")
    site.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )

    response = site.get("/panel/entries/?type=session&status=draft&q=BAL")

    entries = response.context["entries"]
    assert [row.entry.slug for row in entries.rows] == ["bal-w-zamku"]
    assert (entries.entry_type.key, entries.status, entries.query) == (
        "session",
        "draft",
        "BAL",
    )
    assert (entries.total, entries.drafts, entries.published) == (1, 1, 0)
    assert '<input type="hidden" name="type" value="session">' in response.text
    assert '<input type="hidden" name="status" value="draft">' in response.text


def test_the_entries_say_when_nothing_matches(site):
    site.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )

    response = site.get("/panel/entries/?q=nothing-is-called-this")

    assert response.status_code == HTTPStatus.OK
    assert response.context["entries"].rows == ()
    assert "No entry matches." in response.text


@pytest.mark.parametrize(
    "query", ("type=ghost", "status=lost", "page=two", "page=9", "page=0")
)
def test_the_entries_have_no_page_for_what_they_cannot_read(site, query):
    site.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )

    response = site.get(f"/panel/entries/?{query}")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_the_panel_groups_the_demo_types_by_purpose(site):
    site.force_login(
        get_user_model().objects.create_superuser("curator", password="pw")
    )

    response = site.get("/panel/structure/")

    assert response.status_code == HTTPStatus.OK
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
    assert 'href="/panel/entries/?type=session">2 entries</a>' in response.text
    assert 'href="/sesje/">/sesje/</a>' in response.text
    assert 'aria-current="page">Structure</a>' in response.text
    assert "Paid work for an employer" in response.text


def test_the_admin_link_of_a_type_lists_that_type_only(admin):
    for key in ("song", "songbook"):
        EntryType.objects.create(key=key, label=key, route=key)

    response = admin.get("/admin/lapidarium_db/entrytype/?key=song")

    assert response.status_code == HTTPStatus.OK
    assert [t.key for t in response.context["cl"].result_list] == ["song"]


def test_the_entries_link_of_a_type_lists_that_type_only(admin):
    for key in ("song", "songbook"):
        entry_type = EntryType.objects.create(key=key, label=key, route=key)
        Entry.objects.create(type=entry_type, slug=key, title=key)

    response = admin.get("/admin/lapidarium_db/entry/?type=song")

    assert response.status_code == HTTPStatus.OK
    assert [e.slug for e in response.context["cl"].result_list] == ["song"]


def test_the_entries_link_of_a_type_keeps_the_other_filters(admin):
    song = EntryType.objects.create(key="song", label="song", route="song")
    for status in ("draft", "published"):
        Entry.objects.create(type=song, slug=status, title=status, status=status)

    response = admin.get("/admin/lapidarium_db/entry/?type=song&status__exact=draft")

    assert response.status_code == HTTPStatus.OK
    assert [e.slug for e in response.context["cl"].result_list] == ["draft"]


def test_the_entries_link_of_a_type_the_site_lacks_lists_nothing(admin):
    song = EntryType.objects.create(key="song", label="song", route="song")
    Entry.objects.create(type=song, slug="song", title="song")

    response = admin.get("/admin/lapidarium_db/entry/?type=ghost")

    assert response.status_code == HTTPStatus.OK
    assert not response.context["cl"].result_list


def test_the_add_link_of_a_type_opens_the_entry_form_of_that_type(admin):
    for key in ("song", "songbook"):
        EntryType.objects.create(key=key, label=key, route=key)

    response = admin.get("/admin/lapidarium_db/entry/add/?type=song")

    assert response.status_code == HTTPStatus.OK
    assert response.context["adminform"].form.entry_type.key == "song"


def test_the_panel_of_an_empty_site_names_every_purpose(browser):
    browser.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = browser.get("/panel/structure/")

    assert response.status_code == HTTPStatus.OK
    assert [(m.name, m.types) for m in response.context["mechanics"]] == [
        ("Pieces of work", ()),
        ("Events", ()),
        ("Projects", ()),
        ("Activities", ()),
        ("Sections", ()),
    ]
    assert response.text.count("No types yet.") == 5


def test_the_panel_says_nothing_of_a_created_type_it_does_not_have(browser):
    browser.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = browser.get("/panel/structure/?created=ghost")

    assert response.context["created"] is None
    assert "The type is created." not in response.text


def test_the_panel_names_purposes_in_polish(browser):
    browser.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = browser.get("/panel/structure/", HTTP_ACCEPT_LANGUAGE="pl")

    assert '<h2 class="mechanic__name" id="mechanic-thing">Prace</h2>' in response.text
    assert (
        '<a class="btn" href="/panel/new/volunteering/">Nowy: Wolontariat</a>'
        in response.text
    )
    assert "Nieodpłatna praca" in response.text
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
    response = browser.get("/panel/new/volunteering/")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"].startswith("/admin/login/")


def test_any_staff_member_creates_a_type(browser):
    browser.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )

    response = browser.post(
        "/panel/new/volunteering/", {**_VOLUNTEERING, "create": "1"}
    )

    assert response.status_code == HTTPStatus.FOUND
    assert EntryType.objects.filter(key="volunteering").exists()


def test_the_new_type_form_opens_on_what_the_purpose_suggests(browser):
    browser.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = browser.get("/panel/new/volunteering/")

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

    response = browser.get("/panel/new/hobby/")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_preview_shows_the_type_without_saving_it(browser):
    browser.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = browser.post(
        "/panel/new/volunteering/", {**_VOLUNTEERING, "preview": "1"}
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
        "/panel/new/volunteering/", {**_VOLUNTEERING, "create": "1"}
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"] == "/panel/structure/?created=volunteering"
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
    assert panel.context["created"] == "volunteering"
    assert "The type is created." in panel.text
    assert (
        '<a href="/admin/lapidarium_db/entry/add/?type=volunteering">'
        "Add its first entry</a>"
    ) in panel.text
    assert [
        [use.entry_type.key for use in mechanic.types]
        for mechanic in panel.context["mechanics"]
        if mechanic.name == "Activities"
    ] == [["volunteering"]]


def test_create_refuses_what_the_rules_forbid_and_keeps_the_form(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.post(
        "/panel/new/volunteering/",
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
    # The key that needs fixing sits in Advanced.
    assert "<details open>" in response.text
    assert not EntryType.objects.filter(route="about").exists()


def test_create_asks_again_for_what_the_form_cannot_read(browser):
    browser.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = browser.post(
        "/panel/new/volunteering/",
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
    "kind_system": "text",
    "kind_format": "choice",
    "kind_players": "text",
    "new_field_label": "",
    "new_field_kind": "text",
    "allowed_parts": ["text", "video", "image", "audio"],
    "required_parts": ["text"],
    "in_menu": "on",
    "has_detail_page": "on",
    "door_enabled": "on",
}


def test_the_change_form_is_for_staff(site):
    response = site.get("/panel/types/session/")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"].startswith("/admin/login/")


def test_any_staff_member_changes_a_type(site):
    site.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )

    response = site.post(
        "/panel/types/session/", {**_SESSION, "label": "Gra", "save": "1"}
    )

    assert response.status_code == HTTPStatus.FOUND
    assert EntryType.objects.get(key="session").label == "Gra"


def test_an_unknown_type_has_no_change_form(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.get("/panel/types/saga/")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_the_change_form_opens_on_the_settings_of_the_type(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.get("/panel/types/session/")

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
        "kind_system": "text",
        "remove_system": None,
        "kind_format": "choice",
        "remove_format": None,
        "kind_players": "text",
        "remove_players": None,
    }
    assert [field.name for field in form.field_labels] == [
        "field_system",
        "field_format",
        "field_players",
    ]
    assert "I agree to these effects" not in response.text


def test_the_panel_links_each_type_to_its_change_form(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.get("/panel/structure/")

    assert 'href="/panel/types/session/"' in response.text
    assert response.context["changed"] is False


def test_a_change_that_affects_no_entry_is_saved_at_once(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.post(
        "/panel/types/session/",
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
    assert response["Location"] == "/panel/structure/?changed=1"
    changed = EntryType.objects.get(key="session")
    assert (changed.label, changed.route, changed.list_filters) == (
        "Gra",
        "sesje",
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
        "/panel/types/session/",
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

    asked = site.post("/panel/types/session/", moved)

    assert asked.status_code == HTTPStatus.OK
    assert asked.context["change"].consent == "moved::2"
    assert "2 entries move to a new address" in asked.text
    assert EntryType.objects.get(key="session").route == "sesje"

    stale = site.post("/panel/types/session/", {**moved, "agree": "moved::1"})

    assert stale.status_code == HTTPStatus.OK
    assert EntryType.objects.get(key="session").route == "sesje"

    agreed = site.post("/panel/types/session/", {**moved, "agree": "moved::2"})

    assert agreed.status_code == HTTPStatus.FOUND
    assert agreed["Location"] == "/panel/structure/?changed=1"
    assert EntryType.objects.get(key="session").route == "sessions"


def test_pages_lost_are_counted(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))
    data = {k: v for k, v in _SESSION.items() if k != "has_detail_page"}

    lost = site.post("/panel/types/session/", {**data, "preview": "1"})

    assert [(e.kind, e.entries) for e in lost.context["change"].effects] == [
        ("page_lost", 2)
    ]
    assert "2 entries lose their own pages" in lost.text


def test_pages_gained_are_counted(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))
    EntryType.objects.filter(key="session").update(has_detail_page=False)

    gained = site.post("/panel/types/session/", {**_SESSION, "preview": "1"})

    assert [(e.kind, e.entries) for e in gained.context["change"].effects] == [
        ("page_gained", 2)
    ]
    assert "2 entries get their own pages" in gained.text


def test_preview_says_when_a_type_leaves_the_menu(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))
    data = {k: v for k, v in _SESSION.items() if k != "in_menu"}

    response = site.post("/panel/types/session/", {**data, "preview": "1"})

    assert response.context["change"].effects == ()
    assert "outside the menu" in response.text


def test_change_refuses_what_the_rules_forbid_and_keeps_the_form(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.post(
        "/panel/types/session/",
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


def test_preview_refuses_what_the_rules_forbid_and_shows_no_change(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.post(
        "/panel/types/session/", {**_SESSION, "route": "about", "preview": "1"}
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["change"] is None
    assert response.context["form"].errors == {
        "__all__": ["/about/ belongs to the about page."]
    }
    assert EntryType.objects.get(key="session").route == "sesje"


def test_change_asks_again_for_what_the_form_cannot_read(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.post(
        "/panel/types/session/",
        {**_SESSION, "field_system": "", "new_field_kind": "relation", "save": "1"},
    )

    assert response.status_code == HTTPStatus.OK
    assert set(response.context["form"].errors) == {"field_system", "new_field_kind"}
    assert EntryType.objects.get(key="session").label == "Sesja"


def test_the_change_form_offers_a_choice_field_its_own_kind_and_the_plain_ones(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.get("/panel/types/session/")
    form = response.context["form"]
    rows = form.field_rows

    assert [[bound.name for bound in row[1:]] for row in rows] == [
        ["field_system", "kind_system", "remove_system"],
        ["field_format", "kind_format", "remove_format"],
        ["field_players", "kind_players", "remove_players"],
    ]
    plain = ["text", "long_text", "url", "date", "number", "bool"]
    assert [kind for kind, _ in form.fields["kind_system"].choices] == plain
    assert [kind for kind, _ in form.fields["kind_format"].choices] == [
        "choice",
        *plain,
    ]


def test_the_change_form_lists_a_field_labelled_values(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))
    EntryType.objects.get(key="session").fields.filter(key="players").update(
        key="values", label="Values"
    )

    response = site.get("/panel/types/session/")

    assert response.status_code == HTTPStatus.OK
    assert 'name="field_values"' in response.text
    assert 'name="remove_values"' in response.text


def test_a_field_entries_hold_values_for_is_not_removed_or_given_a_new_kind(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    for action in ("save", "preview"):
        response = site.post(
            "/panel/types/session/",
            {
                **_SESSION,
                "label": "Gra",
                "remove_system": "on",
                "kind_players": "long_text",
                action: "1",
            },
        )

        assert response.status_code == HTTPStatus.OK
        assert response.context["change"] is None
        assert response.context["form"].errors == {}
        assert [
            (use.field.key, [entry.slug for entry in use.entries])
            for use in response.context["in_use"]
        ] == [
            ("system", ["bal-w-zamku", "ucieczka-przed-kosmicznym-losiem"]),
            ("players", ["bal-w-zamku", "ucieczka-przed-kosmicznym-losiem"]),
        ]
        assert "2 entries hold a value for the field “System”." in response.text
        assert 'href="/panel/types/session/fields/system/"' in response.text
    unchanged = EntryType.objects.get(key="session")
    assert unchanged.label == "Sesja"
    assert list(unchanged.fields.values_list("key", "kind")) == [
        ("system", "text"),
        ("format", "choice"),
        ("players", "text"),
    ]


def test_a_field_no_entry_holds_a_value_for_is_removed_or_given_a_new_kind(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))
    for entry in Entry.objects.filter(type__key="session"):
        entry.metadata = {"players": entry.metadata["players"], "system": ""}
        entry.save()

    response = site.post(
        "/panel/types/session/",
        {**_SESSION, "remove_system": "on", "kind_format": "text", "save": "1"},
    )

    assert response.status_code == HTTPStatus.FOUND
    changed = EntryType.objects.get(key="session")
    assert changed.list_filters == ["year", "tag", "format"]
    assert list(changed.fields.values_list("key", "kind", "choices")) == [
        ("format", "text", []),
        ("players", "text", []),
    ]


def test_a_relation_field_entries_link_through_is_not_removed(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))
    form = site.get("/panel/types/song/").context["form"]
    shown = {name: form[name].value() for name in form.fields}

    response = site.post(
        "/panel/types/song/",
        {
            **{name: value for name, value in shown.items() if value},
            "remove_inspired_by": "on",
            "save": "1",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert [
        (use.field.key, [entry.slug for entry in use.entries])
        for use in response.context["in_use"]
    ] == [("inspired_by", ["ballada-o-losiu"])]
    assert "1 entry links through the field “Zainspirowana przez”." in response.text
    assert EntryType.objects.get(key="song").fields.filter(key="inspired_by").exists()
    page = site.get("/panel/types/song/fields/inspired_by/")
    assert "Remove these links in each entry first." in page.text


def test_the_entries_of_a_field_are_for_staff(site):
    response = site.get("/panel/types/session/fields/system/")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"].startswith("/admin/login/")


def test_any_staff_member_sees_the_entries_of_a_field(site):
    site.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )

    response = site.get("/panel/types/session/fields/system/")

    assert response.status_code == HTTPStatus.OK


def test_the_entries_of_a_field_link_to_the_admin(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))
    Entry.objects.filter(slug="bal-w-zamku").update(status="draft")

    response = site.get("/panel/types/session/fields/system/")

    assert response.status_code == HTTPStatus.OK
    assert response.context["type_key"] == "session"
    use = response.context["use"]
    assert (use.field.key, [(e.slug, e.status) for e in use.entries]) == (
        "system",
        [("bal-w-zamku", "draft"), ("ucieczka-przed-kosmicznym-losiem", "published")],
    )
    assert response.context["entries_admin"] == "/admin/lapidarium_db/entry/"
    assert 'href="/admin/lapidarium_db/entry/?q=bal-w-zamku"' in response.text
    assert "(draft)" in response.text
    assert 'href="/panel/types/session/"' in response.text


def test_a_field_no_entry_uses_says_so(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))
    Entry.objects.filter(type__key="session").update(metadata={})

    response = site.get("/panel/types/session/fields/system/")

    assert response.context["use"].entries == ()
    assert "No entry uses this field." in response.text


@pytest.mark.parametrize("path", ("saga/fields/system", "session/fields/mood"))
def test_an_unknown_field_has_no_entries_page(site, path):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.get(f"/panel/types/{path}/")

    assert response.status_code == HTTPStatus.NOT_FOUND


_PROFILE = {
    "name": "Mira K.",
    "handle": "@mira",
    "tagline": "Games and songs.",
    "bio": "Hello.",
    "email": "",
    "friends_title": "Znajomi",
    "friends_intro": "",
}


def test_the_site_page_is_for_staff(site):
    response = site.get("/panel/site/")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"].startswith("/admin/login/")


def test_the_site_page_opens_on_the_profile(site):
    site.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )
    profile = Profile.objects.get()

    response = site.get("/panel/site/")

    assert response.status_code == HTTPStatus.OK
    assert response.context["saved"] is False
    assert response.context["form"].initial == {
        "name": profile.name,
        "handle": profile.handle,
        "tagline": profile.tagline,
        "bio": profile.bio,
        "email": profile.email,
        "friends_title": profile.friends_title,
        "friends_intro": profile.friends_intro,
    }
    assert 'aria-current="page">Site</a>' in response.text
    assert ">Admin</a>" not in response.text


def test_the_site_page_of_an_empty_site_opens_blank(browser):
    browser.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = browser.get("/panel/site/")

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].initial == {}
    assert '<a href="/admin/">Admin</a>' in response.text


def test_the_site_page_saves_the_texts_and_keeps_the_photo(site):
    site.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )
    before = Profile.objects.get()

    response = site.post("/panel/site/", _PROFILE)

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"] == "/panel/site/?saved=1"
    after = Profile.objects.get()
    assert {key: getattr(after, key) for key in _PROFILE} == _PROFILE
    assert (after.photo_id, after.button_id) == (before.photo_id, before.button_id)
    saved = site.get(response["Location"])
    assert saved.context["saved"] is True
    assert "The profile is saved." in saved.text
    assert "Mira K." in site.get("/about/").text


def test_the_site_page_keeps_the_form_when_it_cannot_read_it(site):
    site.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )
    name = Profile.objects.get().name

    response = site.post("/panel/site/", {**_PROFILE, "name": "", "email": "nope"})

    assert response.status_code == HTTPStatus.OK
    assert set(response.context["form"].errors) == {"name", "email"}
    assert Profile.objects.get().name == name
