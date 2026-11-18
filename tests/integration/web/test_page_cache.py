"""Rendered pages are kept until content changes."""

import pytest
import yaml
from django.core.cache import caches

from lapidarium.inits import Services
from lapidarium.links.db.django.models import Entry, EntryType, Tag
from lapidarium.pacts.content import PAGE_CACHE

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


@pytest.fixture(name="page_cache")
def page_cache_fixture(settings):
    settings.CACHES = {
        **settings.CACHES,
        PAGE_CACHE: {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    }
    caches[PAGE_CACHE].clear()


@pytest.fixture(name="cached_site")
def cached_site_fixture(page_cache, site):
    del page_cache  # Requested for its effect: an empty page cache.
    return site


def test_pages_are_served_from_the_cache_until_content_changes(
    cached_site, django_capture_on_commit_callbacks
):
    assert cached_site.get("/sesje/bal-w-zamku/").context is not None
    # A cached response is not rendered again, so it has no template context.
    assert cached_site.get("/sesje/bal-w-zamku/").context is None

    with django_capture_on_commit_callbacks(execute=True):
        Entry.objects.filter(slug="bal-w-zamku").get().save()

    assert cached_site.get("/sesje/bal-w-zamku/").context is not None


@pytest.mark.parametrize(
    "change",
    (
        lambda: EntryType.objects.get(key="session").save(),
        lambda: Entry.objects.get(slug="bal-w-zamku").delete(),
        lambda: Entry.objects.get(slug="ballada-o-losiu").tags.add(
            Tag.objects.create(name="szanta")
        ),
    ),
)
def test_any_content_change_clears_the_cache(
    *, cached_site, django_capture_on_commit_callbacks, change
):
    cached_site.get("/")
    assert cached_site.get("/").context is None

    with django_capture_on_commit_callbacks(execute=True):
        change()

    assert cached_site.get("/").context is not None


def _import_profile(root, friends):
    (root / "lapidarium.yaml").write_text("format: 1\n", encoding="utf-8")
    profile = {"name": "Mira", "friends": friends}
    (root / "profile.yaml").write_text(yaml.safe_dump(profile), encoding="utf-8")
    Services().content.importer.import_from(root)


@pytest.mark.usefixtures("page_cache")
def test_import_clears_the_cache_when_its_writes_send_no_signal(
    *, browser, tmp_path, django_capture_on_commit_callbacks
):
    _import_profile(tmp_path, [])
    browser.get("/about/")
    assert browser.get("/about/").context is None

    # The profile is updated and the friend bulk-inserted: neither sends a signal.
    friend = {"name": "Kostka i Pióro", "url": "https://kostka.example.org"}
    with django_capture_on_commit_callbacks(execute=True):
        _import_profile(tmp_path, [friend])

    assert "Kostka i Pióro" in browser.get("/about/").content.decode()
