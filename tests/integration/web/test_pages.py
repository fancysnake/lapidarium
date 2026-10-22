"""About, what's new, search and the feeds."""

import datetime as dt
from http import HTTPStatus

import pytest
from django.template.loader import render_to_string
from django.utils import timezone

from lapidarium.links.db.django.models import Entry, ExternalItem, Link, Profile
from lapidarium.pacts import FeedChange
from tests.integration.web.conftest import NOW

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


def test_about_shows_profile_links_and_timeline(site):
    response = site.get("/about/")

    assert response.status_code == HTTPStatus.OK
    site_dto = response.context["site"]
    assert site_dto.profile.name == "Mira Kowalska"
    assert [link.label for link in site_dto.links] == ["YouTube", "itch.io"]
    assert [c.entry.slug for c in response.context["timeline"]] == [
        "prowadzenie",
        "klatwa-strahda",
        "kampania-mothership",
        "sesje-science-fiction",
    ]
    assert response.context["can_contact"] is True
    assert response.context["current_page"] == "about"
    assert "Mistrzyni gry od piętnastu lat." in response.text


def test_about_without_a_profile(browser):
    response = browser.get("/about/")

    assert response.context["site"].profile is None
    assert response.context["can_contact"] is False
    assert response.context["timeline"] == ()
    assert "Where to find me" not in response.text


def test_about_without_photo_or_contact(site):
    Profile.objects.update(photo=None, handle="", tagline="", email="")
    Link.objects.all().delete()

    response = site.get("/about/")

    assert response.context["can_contact"] is False
    assert "Where to find me" not in response.text


def test_whats_new_lists_entries_and_feed_items(site):
    ExternalItem.objects.create(
        source="YouTube",
        external_id="x",
        title="Stream",
        url="https://youtu.be/x",
        published_at=NOW,
    )
    Entry.objects.filter(slug="bal-w-zamku").update(created_at=NOW.replace(year=2025))

    response = site.get("/new/")

    items = response.context["items"]
    assert len(items) == 14
    assert {i.change for i in items} == {
        FeedChange.ADDED,
        FeedChange.UPDATED,
        FeedChange.EXTERNAL,
    }
    assert "(updated)" in response.text
    assert 'href="https://youtu.be/x"' in response.text


def test_whats_new_when_nothing_is_new(browser):
    response = browser.get("/new/")

    assert response.context["items"] == ()
    assert "Nothing here yet." in response.text


@pytest.mark.parametrize(
    ("query", "found"),
    (("", []), ("lodz", []), ("Tycho", ["ucieczka-przed-kosmicznym-losiem"])),
)
def test_search(*, site, query, found):
    response = site.get("/search/", {"q": query})

    assert response.context["query"] == query
    assert [c.entry.slug for c in response.context["results"]] == found
    assert ("Nothing matches" in response.text) is bool(query and not found)


def test_rss_carries_whats_new(site):
    response = site.get("/rss.xml")

    assert response["Content-Type"].startswith("application/rss+xml")
    assert "<title>Mira Kowalska</title>" in response.text
    assert "<link>http://testserver/memy/#los-w-kosmosie</link>" in response.text
    assert "<pubDate>Wed, 14 Oct 2026 12:00:00 +0000</pubDate>" in response.text


def test_rss_of_a_profile_less_site_links_feed_items(browser):
    ExternalItem.objects.create(
        source="YouTube",
        external_id="x",
        title="Stream",
        url="https://youtu.be/x",
        published_at=NOW,
    )

    response = browser.get("/rss.xml")

    assert "<title>lapidarium (test)</title>" in response.text
    assert "<link>https://youtu.be/x</link>" in response.text


def test_ical_lists_upcoming_calendar_entries(site):
    response = site.get("/calendar.ics")

    assert response["Content-Type"] == "text/calendar; charset=utf-8"
    assert response.text.count("BEGIN:VEVENT") == 2
    assert "UID:event-pyrkon-2027@testserver\r\n" in response.text
    assert "URL:http://testserver/wydarzenia/pyrkon-2027/\r\n" in response.text
    assert "X-WR-CALNAME:Mira Kowalska\r\n" in response.text


def test_ical_of_a_profile_less_site(browser):
    response = browser.get("/calendar.ics")

    assert "X-WR-CALNAME:lapidarium (test)\r\n" in response.text
    assert "BEGIN:VEVENT" not in response.text


def test_server_errors_have_a_page_of_their_own():
    html = render_to_string("500.html")

    assert "<h1>Something broke</h1>" in html


def test_footer_credits_the_owner_and_the_engine_apart(site):
    Profile.objects.update(name="Ola Nowak")
    year = dt.datetime.now(timezone.get_current_timezone()).year

    response = site.get("/")

    assert f"© {year} Ola Nowak." in response.text
    assert (
        'This site runs on <a href="https://github.com/fancysnake/lapidarium">'
        "Lapidarium</a> © 2026 fancysnake, MIT licence." in response.text
    )


def test_footer_credits_in_polish(site):
    response = site.get("/", HTTP_ACCEPT_LANGUAGE="pl")

    assert "Strona działa na <a" in response.text
    assert "© 2026 fancysnake, licencja MIT." in response.text
