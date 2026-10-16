from http import HTTPStatus

import pytest

from lapidarium.links.db.django.models import (
    Entry,
    EntryType,
    MediaAsset,
    Part,
    Profile,
)

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


def test_a_session_page_brings_its_relations(site):
    response = site.get("/sesje/ucieczka-przed-kosmicznym-losiem/")

    assert response.status_code == HTTPStatus.OK
    detail = response.context["detail"]
    assert detail.card.entry.title == "Ucieczka przed kosmicznym łosiem"
    assert [f.label for f in detail.panel] == ["System", "Format", "Gracze"]
    assert [c.slug for c in detail.containers] == ["kampania-mothership"]
    assert [c.entry.slug for c in detail.related] == [
        "ballada-o-losiu",
        "los-w-kosmosie",
    ]
    assert detail.siblings == ()
    assert detail.contents == ()
    assert response.context["layout"] == "lapidarium/layouts/media_first.html"
    assert 'data-embed-url="https://www.youtube-nocookie.com/embed/' in response.text
    assert '<meta property="og:title" content="Ucieczka przed kosmicznym łosiem">' in (
        response.text
    )
    assert 'href="/sesje/?tag=sci-fi"' in response.text


def test_a_song_links_what_inspired_it_and_plays_from_its_provider(site):
    response = site.get("/piosenki/ballada-o-losiu/")

    detail = response.context["detail"]
    assert [ref.slug for ref in detail.panel[0].refs] == [
        "ucieczka-przed-kosmicznym-losiem"
    ]
    assert 'href="https://soundcloud.com/example/ballada-o-losiu"' in response.text
    assert "Słowa" in response.text


def test_a_container_lists_its_contents(site):
    response = site.get("/projekty/kampania-mothership/")

    detail = response.context["detail"]
    assert [c.entry.slug for c in detail.contents] == [
        "ucieczka-przed-kosmicznym-losiem"
    ]
    assert "Inside" in response.text
    assert "finished" in response.text


def test_entries_in_one_container_point_at_each_other(site):
    Entry.objects.get(slug="bal-w-zamku").relations.update(
        to_entry=Entry.objects.get(slug="kampania-mothership")
    )

    response = site.get("/sesje/bal-w-zamku/")

    assert [c.entry.slug for c in response.context["detail"].siblings] == [
        "ucieczka-przed-kosmicznym-losiem"
    ]
    assert "More from" in response.text


def test_an_article_shows_cover_parts_and_external_page(site):
    response = site.get("/gry/krotkie-nogi/")

    assert response.context["layout"] == "lapidarium/layouts/article.html"
    assert 'class="detail-hero__cover"' in response.text
    assert "Open on example.itch.io" in response.text
    assert 'property="og:image" content="http://testserver/media/' in response.text


def test_calendar_entries_show_when_and_where(site):
    response = site.get("/wydarzenia/pyrkon-2027/")

    assert "Starts" in response.text
    assert "Ends" in response.text
    assert "Poznań" in response.text


def test_online_entries_say_so(site):
    response = site.get("/wydarzenia/sesje-online/")

    assert "(online)" in response.text


def test_every_part_kind_renders(site):
    entry = Entry.objects.get(slug="krotkie-nogi")
    asset = MediaAsset.objects.get(file="assets/demo/krotkie-nogi.svg")
    EntryType.objects.filter(key="game").update(layout="gallery")
    entry.license = "CC BY 4.0"
    entry.save()
    Part.objects.filter(entry=entry).delete()
    Part.objects.bulk_create(
        [
            Part(entry=entry, order=0, kind="image", asset=asset, caption="Okładka"),
            Part(entry=entry, order=1, kind="file", asset=asset),
            Part(
                entry=entry,
                order=2,
                kind="file",
                asset=asset,
                options={"download_label": "Zasady (PDF)"},
            ),
            Part(entry=entry, order=3, kind="audio", asset=asset, caption="Motyw"),
            Part(entry=entry, order=4, kind="video", url="https://example.com/v.mp4"),
            Part(entry=entry, order=5, kind="link", url="https://example.com/x"),
            Part(entry=entry, order=6, kind="text", text="**Bold** <script>x</script>"),
        ]
    )

    response = site.get("/gry/krotkie-nogi/")

    text = response.text
    assert response.context["layout"] == "lapidarium/layouts/gallery.html"
    assert "<figcaption>Okładka</figcaption>" in text
    assert "krotkie-nogi.svg</strong>" in text
    assert "Zasady (PDF)" in text
    assert "<audio controls" in text
    assert "<figcaption>Motyw</figcaption>" in text
    assert 'href="https://example.com/v.mp4"' in text
    assert 'href="https://example.com/x"' in text
    assert "<strong>Bold</strong>" in text
    assert "<script>x" not in text
    assert "CC BY 4.0" in text


def test_a_profile_less_site_has_no_author_box(site):
    Profile.objects.all().delete()

    response = site.get("/artykuly/jak-prowadzic-one-shoty/")

    assert response.context["site"].profile is None
    assert "author-box" not in response.text


@pytest.mark.parametrize(
    "path", ("/sesje/nope/", "/memy/los-w-kosmosie/", "/nope/bal-w-zamku/")
)
def test_missing_and_list_only_entries_are_not_found(site, path):
    assert site.get(path).status_code == HTTPStatus.NOT_FOUND


def test_media_first_entries_show_their_cover_url_and_bool_fields(site):
    session_type = EntryType.objects.get(key="session")
    session_type.fields.create(key="vod", label="VOD", kind="url", order=9)
    session_type.fields.create(key="safe", label="Safety tools", kind="bool")
    entry = Entry.objects.get(slug="bal-w-zamku")
    entry.cover = MediaAsset.objects.get(file="assets/demo/los.svg")
    entry.metadata = {
        **entry.metadata,
        "vod": "https://www.twitch.tv/videos/1",
        "safe": True,
    }
    entry.save()

    response = site.get("/sesje/bal-w-zamku/")

    assert 'class="detail-hero__cover"' in response.text
    assert '<a href="https://www.twitch.tv/videos/1" rel="noopener">twitch.tv</a>' in (
        response.text
    )
    assert "<dt>Safety tools</dt>" in response.text
