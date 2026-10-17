from http import HTTPStatus

import pytest

from lapidarium.links.db.django.models import Entry, EntryType
from lapidarium.pacts import FilterDTO

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


def test_a_type_lists_its_entries_with_filters(site):
    response = site.get("/sesje/")

    assert response.status_code == HTTPStatus.OK
    listing = response.context["listing"]
    assert listing.entry_type.key == "session"
    assert [c.entry.slug for c in listing.cards] == [
        "bal-w-zamku",
        "ucieczka-przed-kosmicznym-losiem",
    ]
    assert listing.filters == (
        FilterDTO(key="year", label="", options=("2026",), selected=""),
        FilterDTO(
            key="tag", label="", options=("groza", "one-shot", "sci-fi"), selected=""
        ),
        FilterDTO(
            key="system", label="System", options=("D&D 5e", "Mothership"), selected=""
        ),
        FilterDTO(
            key="format",
            label="Format",
            options=("campaign-session", "one-shot"),
            selected="",
        ),
    )
    assert (listing.page, listing.pages, listing.total) == (1, 1, 2)
    assert response.context["current_route"] == "sesje"
    assert f'aria-current="page">{listing.entry_type.label_plural}</a>' in response.text


def test_filters_narrow_the_list(site):
    response = site.get("/sesje/?tag=groza&year=2026")

    listing = response.context["listing"]
    assert [c.entry.slug for c in listing.cards] == ["bal-w-zamku"]
    assert [f.selected for f in listing.filters] == ["2026", "groza", "", ""]


def test_nothing_matching_says_so(site):
    Entry.objects.filter(type__key="article").delete()

    response = site.get("/artykuly/")

    assert response.context["listing"].cards == ()
    assert "Nothing here yet." in response.text


def test_calendar_types_split_upcoming_and_archive(site):
    response = site.get("/wydarzenia/")

    listing = response.context["listing"]
    assert [c.entry.slug for c in listing.upcoming] == ["sesje-online", "pyrkon-2027"]
    assert [c.entry.slug for c in listing.cards] == ["copernicon-2026"]
    assert "Archive" in response.text


def test_gallery_types_show_images_with_anchors(site):
    response = site.get("/memy/")

    listing = response.context["listing"]
    assert [c.entry.slug for c in listing.cards] == ["los-w-kosmosie"]
    assert 'id="los-w-kosmosie"' in response.text
    assert 'href="#los-w-kosmosie"' in response.text


def test_gallery_entries_without_cover_show_their_images(site):
    Entry.objects.filter(slug="los-w-kosmosie").update(cover=None)

    response = site.get("/memy/")

    assert 'src="/media/assets/demo/los.svg"' in response.text


def test_pages_link_both_ways(site):
    session = Entry.objects.get(slug="bal-w-zamku")
    for day in range(11):
        session.pk = None
        session.slug = f"copy-{day}"
        session.save()

    first = site.get("/sesje/")
    second = site.get("/sesje/?page=2")

    assert first.context["listing"].pages == 2
    assert 'rel="next"' in first.text
    assert 'rel="prev"' in second.text
    assert "Page 2 of 2" in second.text


@pytest.mark.parametrize("path", ("/nope/", "/sesje/?page=9", "/sesje/?page=x"))
def test_unknown_lists_and_pages_are_not_found(site, path):
    response = site.get(path)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.templates[0].name == "404.html"
    assert "Not found" in response.text


def test_gallery_types_with_detail_pages_link_to_them(site):
    EntryType.objects.filter(key="meme").update(has_detail_page=True)

    response = site.get("/memy/")

    assert 'href="/memy/los-w-kosmosie/"' in response.text
