"""Rendered pages are kept until content changes."""

import pytest
from django.core.cache import caches

from lapidarium.links.db.django.models import Entry, EntryType, Tag
from lapidarium.pacts.site import PAGE_CACHE

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


@pytest.fixture(name="cached_site")
def cached_site_fixture(settings, site):
    settings.CACHES = {
        **settings.CACHES,
        PAGE_CACHE: {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    }
    caches[PAGE_CACHE].clear()
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
