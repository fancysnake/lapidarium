import datetime as dt
import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from dulwich import porcelain

from lapidarium.links.db.django.models import Entry, ExternalItem, Profile
from lapidarium.links.feeds.atom import AtomFeed
from lapidarium.pacts import DeliveryError

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root", "demo")]
ITEM = {
    "source": "YouTube",
    "external_id": "yt:video:dQw4w9WgXcQ",
    "title": "Moose stream",
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "published_at": dt.datetime(2026, 10, 1, tzinfo=dt.UTC),
    "thumbnail_url": "",
}


def _run(*args):
    out = StringIO()
    call_command(*args, stdout=out)
    return out.getvalue()


def test_fetch_feeds_saves_and_links_items(settings, monkeypatch):
    settings.FEED_SOURCES = ["youtube:UC1"]
    monkeypatch.setattr(AtomFeed, "fetch", lambda _self: [ITEM])

    output = _run("fetch_feeds")

    assert output == "Fetched 1 items: 1 new, 1 linked to entries.\n"
    item = ExternalItem.objects.get()
    assert item.entry == Entry.objects.get(slug="ucieczka-przed-kosmicznym-losiem")


def test_fetch_feeds_names_sources_it_could_not_read(settings, monkeypatch):
    settings.FEED_SOURCES = ["github:o/r"]

    def fail(_self):
        raise DeliveryError

    monkeypatch.setattr(AtomFeed, "fetch", fail)

    with pytest.raises(CommandError, match=r"Could not read: GitHub https://github"):
        _run("fetch_feeds")


def test_check_content_lists_issues_and_fails(mailoutbox):
    out = StringIO()
    with pytest.raises(CommandError, match="to look at") as raised:
        call_command("check_content", "--mail", stdout=out)

    assert raised.value.returncode == 1
    lines = out.getvalue().splitlines()
    assert "H002 The Artykuły door has too few entries to show." in lines
    assert "H003 event/copernicon-2026: It is over and nothing from it is linked." in (
        lines
    )
    [digest] = mailoutbox
    assert digest.to == ["mira@example.com"]


def test_check_content_as_json():
    out = StringIO()
    with pytest.raises(CommandError):
        call_command("check_content", "--json", stdout=out)

    issues = json.loads(out.getvalue())
    assert issues[0] == {
        "code": "H002",
        "message": "The Artykuły door has too few entries to show.",
        "entry": None,
    }


def test_check_content_mail_needs_an_address():
    Profile.objects.update(email="")

    with pytest.raises(CommandError, match="Could not mail the digest"):
        call_command("check_content", "--mail", stdout=StringIO())


def test_check_content_passes_on_healthy_content(monkeypatch):
    def healthy(_self, **_options):
        return []

    monkeypatch.setattr("lapidarium.mills.health.ContentHealthService.check", healthy)

    assert not _run("check_content", "--links")


def test_export_commits_into_a_working_copy(tmp_path):
    porcelain.init(str(tmp_path))

    first = _run("export_content", str(tmp_path), "--commit")
    again = _run("export_content", str(tmp_path), "--commit")

    assert first == "Exported 9 types, 13 entries, 3 assets. Committed.\n"
    assert again == "Exported 9 types, 13 entries, 3 assets.\n"


def test_export_commit_needs_a_working_copy(tmp_path):
    with pytest.raises(CommandError, match="is not a git repository"):
        _run("export_content", str(tmp_path), "--push")
