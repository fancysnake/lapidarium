from http import HTTPStatus

import pytest

from lapidarium.links.db.django.models import Entry, EntryType, Profile, Showcase
from lapidarium.pacts.catalogue import FeedChange
from lapidarium.pacts.content import EntryStatus

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


def test_home_shows_doors_whats_new_and_the_next_event(site):
    response = site.get("/")

    assert response.status_code == HTTPStatus.OK
    home = response.context["home"]
    assert [(d.entry_type.key, d.label, d.pick.entry.slug) for d in home.doors] == [
        ("session", "Sesje RPG", "bal-w-zamku"),
        ("song", "Piosenki", "ballada-o-losiu"),
        ("game", "Gry", "krotkie-nogi"),
        ("meme", "Memy", "los-w-kosmosie"),
        ("event", "Wydarzenia", "sesje-online"),
    ]
    assert len(home.whats_new) == 5
    assert {item.change for item in home.whats_new} == {FeedChange.ADDED}
    assert home.next_up.entry.slug == "sesje-online"
    site_dto = response.context["site"]
    assert site_dto.profile.name == "Mira Kowalska"
    assert [t.key for t in site_dto.menu] == [
        "session",
        "song",
        "game",
        "meme",
        "event",
        "article",
        "project",
        "initiative",
    ]
    assert response.context["site_name"] == "lapidarium (test)"
    assert response.context["current_page"] == "home"
    assert not response.context["current_route"]
    assert (
        '[data-type="session"] { --type-color: #6b3fa0; --type-tint:' in response.text
    )
    assert 'href="/contact/"' in response.text


def test_home_shows_showcases_as_bands_in_their_type_colour(site):
    response = site.get("/")

    showcases = response.context["home"].showcases
    assert [
        (s.title, s.type_key, [c.entry.slug for c in s.cards]) for s in showcases
    ] == [
        (
            "Jak lubię grać",
            "",
            ["jak-prowadzic-one-shoty", "bal-w-zamku", "krotkie-nogi"],
        ),
        ("Piosenki, o które pytacie", "song", ["ballada-o-losiu"]),
    ]
    assert showcases[0].intro.startswith("Od tego warto zacząć")
    assert '<section class="showcase"\n         data-type=""' in response.text
    assert '<section class="showcase"\n         data-type="song"' in response.text
    assert 'href="/piosenki/ballada-o-losiu/"' in response.text
    assert response.text.count('class="showcase__more"') == 4


def test_home_leaves_out_hidden_showcases_and_those_left_empty(site):
    Showcase.objects.filter(title="Jak lubię grać").update(hidden=True)
    Entry.objects.filter(slug="ballada-o-losiu").update(status=EntryStatus.DRAFT)

    response = site.get("/")

    assert response.context["home"].showcases == ()
    assert 'class="showcase"' not in response.text


def test_an_empty_site_still_has_a_home_page(browser):
    response = browser.get("/")

    assert response.status_code == HTTPStatus.OK
    assert response.context["home"].doors == ()
    assert response.context["home"].showcases == ()
    assert response.context["home"].whats_new == ()
    assert response.context["home"].next_up is None
    assert response.context["site"].profile is None
    assert "Nothing here yet." in response.text
    assert 'href="/contact/"' not in response.text


def test_the_portrait_takes_the_hero_aside_without_an_upcoming_event(site):
    Entry.objects.filter(type__key="event").delete()

    response = site.get("/")

    assert response.context["home"].next_up is None
    assert response.context["site"].profile.photo is not None
    assert 'class="hero__portrait"' in response.text


def test_a_profile_without_photo_or_tagline(site):
    Profile.objects.update(photo=None, tagline="", handle="", email="")
    EntryType.objects.update(door_enabled=False)
    Entry.objects.filter(type__key="event").delete()

    response = site.get("/")

    assert response.context["site"].profile.photo is None
    assert response.context["home"].doors == ()
    assert response.context["home"].next_up is None
    assert "hero__portrait" not in response.text
