"""About, what's new, search and the feeds."""

import datetime as dt
from http import HTTPStatus

import pytest
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

from lapidarium.links.db.django.models import (
    Entry,
    ExternalItem,
    Friend,
    Link,
    MediaAsset,
    Profile,
)
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


def test_about_lists_friends_as_text_buttons_with_a_link_back(site):
    response = site.get("/about/")

    friends = response.context["friends"]
    assert [(f.name, f.url, f.button) for f in friends] == [
        ("Kostka i Pióro", "https://kostka.example.org", None),
        ("Gotycki Kufer", "https://kufer.example.net", None),
    ]
    assert "> Przyjaciele stołu </h2>" in " ".join(response.text.split())
    assert "Strony ludzi, z którymi gram, piszę i śpiewam." in response.text
    assert (
        '<a class="web-button" href="https://kostka.example.org"'
        ' rel="external noopener">'
    ) in response.text
    assert '<span class="web-button__text">Gotycki Kufer</span>' in response.text
    assert '<a href="http://testserver/">Mira Kowalska</a>' in response.text
    assert (
        "<code>&lt;a href=&quot;http://testserver/&quot;&gt;"
        "Mira Kowalska&lt;/a&gt;</code>"
    ) in response.text


def test_about_shows_friend_and_own_buttons_as_images(site):
    friend_button = MediaAsset.objects.create(file=ContentFile(b"", name="ada.png"))
    own_button = MediaAsset.objects.create(file=ContentFile(b"", name="mira.png"))
    Friend.objects.all().delete()
    Friend.objects.create(
        name="Ada", url="https://ada.example.org", button=friend_button
    )
    Profile.objects.update(button=own_button, friends_title="", friends_intro="")

    response = site.get("/about/")

    text = " ".join(response.text.split())
    assert "> Friends </h2>" in text
    assert f'src="{friend_button.file.url}" width="88" height="31" alt="Ada"' in text
    assert (
        '<a href="http://testserver/">'
        f'<img src="http://testserver{own_button.file.url}"'
        ' width="88" height="31" alt="Mira Kowalska"></a>'
    ) in text
    assert (
        "&lt;a href=&quot;http://testserver/&quot;&gt;&lt;img"
        f" src=&quot;http://testserver{own_button.file.url}&quot;"
        " width=&quot;88&quot; height=&quot;31&quot;"
        " alt=&quot;Mira Kowalska&quot;&gt;&lt;/a&gt;"
    ) in text


def test_about_without_friends_or_a_button_has_no_friends_section(site):
    Friend.objects.all().delete()

    response = site.get("/about/")

    assert 'class="friends"' not in response.text


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


def test_footer_without_a_profile_name_claims_only_the_engine(site):
    Profile.objects.update(name="")

    response = site.get("/")

    assert response.text.count("©") == 1
    assert "© 2026 fancysnake, MIT licence." in response.text


def test_footer_credits_in_polish(site):
    response = site.get("/", HTTP_ACCEPT_LANGUAGE="pl")

    assert "Strona działa na <a" in response.text
    assert "© 2026 fancysnake, licencja MIT." in response.text
