import datetime as dt

import httpx
import pytest
from dulwich import porcelain
from dulwich.repo import Repo

from lapidarium.links.archive.git import GitArchive
from lapidarium.links.db.django.models import Entry, EntryType, ExternalItem
from lapidarium.links.db.django.repositories import ExternalItemRepository
from lapidarium.links.feeds.atom import AtomFeed, youtube
from lapidarium.links.linkcheck.httpx import HttpLinkChecker
from lapidarium.pacts import DeliveryError, NotFoundError

YOUTUBE = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
 <title>Mira</title>
 <entry>
  <id>yt:video:abc</id>
  <title>Moose stream</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=abc"/>
  <published>2026-10-01T18:00:00+00:00</published>
  <updated>2026-10-02T18:00:00+00:00</updated>
  <media:group><media:thumbnail url="https://i.ytimg.com/vi/abc/hq.jpg"/></media:group>
 </entry>
 <entry><id>yt:video:nolink</id><title>Broken</title></entry>
</feed>"""
GITHUB = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
 <entry>
  <id>tag:github.com,2008:Repository/1/v1.0</id>
  <updated>2026-09-01T10:00:00Z</updated>
  <link rel="alternate" type="text/html" href="https://github.com/o/r/releases/tag/v1.0"/>
  <title>v1.0</title>
 </entry>
</feed>"""
BOMB = b"""<?xml version="1.0"?>
<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;">]>
<feed xmlns="http://www.w3.org/2005/Atom"><title>&lol2;</title></feed>"""


def _feed(content=b"", *, status=200, error=None):
    def handler(request):
        if error:
            msg = "down"
            raise error(msg, request=request)
        return httpx.Response(status, content=content)

    source, url = youtube("UC1")
    return AtomFeed(source=source, url=url, transport=httpx.MockTransport(handler))


def test_youtube_feed_items():
    items = _feed(YOUTUBE).fetch()

    assert items == [
        {
            "source": "YouTube",
            "external_id": "yt:video:abc",
            "title": "Moose stream",
            "url": "https://www.youtube.com/watch?v=abc",
            "published_at": dt.datetime(2026, 10, 1, 18, tzinfo=dt.UTC),
            "thumbnail_url": "https://i.ytimg.com/vi/abc/hq.jpg",
        }
    ]


def test_github_release_feed_items_date_by_update():
    [item] = _feed(GITHUB).fetch()

    assert item["url"] == "https://github.com/o/r/releases/tag/v1.0"
    assert item["published_at"] == dt.datetime(2026, 9, 1, 10, tzinfo=dt.UTC)
    assert not item["thumbnail_url"]


def test_a_link_without_rel_is_taken():
    feed = GITHUB.replace(b'rel="alternate" type="text/html" ', b"")

    assert len(_feed(feed).fetch()) == 1


@pytest.mark.parametrize(
    "feed",
    (_feed(status=503), _feed(error=httpx.ConnectError), _feed(b"<feed"), _feed(BOMB)),
)
def test_unreadable_feeds_are_delivery_errors(feed):
    with pytest.raises(DeliveryError):
        feed.fetch()


def _checker(routes):
    def handler(request):
        outcome = routes[request.method, request.url.path]
        if isinstance(outcome, type):
            msg = "down"
            raise outcome(msg, request=request)
        return httpx.Response(outcome)

    return HttpLinkChecker(transport=httpx.MockTransport(handler))


def test_link_checker():
    checker = _checker(
        {
            ("HEAD", "/ok"): 200,
            ("HEAD", "/no-head"): 405,
            ("GET", "/no-head"): 200,
            ("HEAD", "/gone"): 404,
            ("HEAD", "/down"): httpx.ConnectError,
            ("HEAD", "/flaky"): 403,
            ("GET", "/flaky"): httpx.ConnectError,
        }
    )

    assert [
        checker.is_alive(f"https://example.com/{path}")
        for path in ("ok", "no-head", "gone", "down", "flaky")
    ] == [True, True, False, False, False]


@pytest.mark.django_db
def test_saving_external_items_creates_updates_and_links():
    entry = Entry.objects.create(
        type=EntryType.objects.create(key="talk", route="talks"),
        slug="moose",
        title="Moose",
        summary="One.",
    )
    item = {
        "source": "YouTube",
        "external_id": "yt:video:abc",
        "title": "Moose",
        "url": "https://www.youtube.com/watch?v=abc",
        "published_at": dt.datetime(2026, 10, 1, tzinfo=dt.UTC),
        "thumbnail_url": "",
    }
    repository = ExternalItemRepository()

    assert repository.save(item, entry=None) is True
    assert (
        repository.save({**item, "title": "Renamed"}, entry=("talk", "moose")) is False
    )

    saved = ExternalItem.objects.get()
    assert (saved.title, saved.entry) == ("Renamed", entry)


@pytest.fixture(name="working_copy")
def working_copy_fixture(tmp_path):
    root = tmp_path / "export"
    porcelain.init(str(root))
    return root


def _messages(root):
    with Repo(str(root)) as repo:
        return [entry.commit.message for entry in repo.get_walker()]


def test_archive_commits_additions_changes_and_removals(working_copy):
    archive = GitArchive()
    (working_copy / "a.md").write_text("one")
    (working_copy / "b.md").write_text("two")

    assert archive.commit(working_copy, message="First") is True
    assert archive.commit(working_copy, message="Nothing") is False

    (working_copy / "a.md").write_text("changed")
    (working_copy / "b.md").unlink()
    assert archive.commit(working_copy, message="Second") is True

    assert _messages(working_copy) == [b"Second", b"First"]
    with Repo(str(working_copy)) as repo:
        tree = repo[repo[repo.head()].tree]
        assert [entry.path for entry in tree.iteritems()] == [b"a.md"]


def test_archive_pushes_to_its_remote(tmp_path, working_copy):
    remote = tmp_path / "remote.git"
    porcelain.init(str(remote), bare=True)
    with Repo(str(working_copy)) as repo:
        config = repo.get_config()
        config.set((b"remote", b"origin"), b"url", str(remote).encode())
        config.write_to_path()
    (working_copy / "a.md").write_text("one")
    archive = GitArchive()
    archive.commit(working_copy, message="First")

    archive.push(working_copy)

    with Repo(str(remote)) as bare:
        branch = b"refs/heads/" + porcelain.active_branch(str(working_copy))
        assert bare[bare.refs[branch]].message == b"First"


def test_archive_push_without_a_remote_is_refused(working_copy):
    (working_copy / "a.md").write_text("one")
    GitArchive().commit(working_copy, message="First")

    with pytest.raises(DeliveryError):
        GitArchive().push(working_copy)


def test_archive_needs_a_git_repository(tmp_path):
    with pytest.raises(NotFoundError):
        GitArchive().commit(tmp_path, message="x")
