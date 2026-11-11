"""The content panel: staff see the site's types grouped by what they are for."""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model

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
    assert "/admin/lapidarium_db/entrytype/?q=song" in response.text
    assert "Paid work for an employer" in response.text


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
    assert "<strong>Wolontariat</strong>: Nieodpłatna praca" in response.text
    assert "Nie ma jeszcze rodzajów." in response.text
