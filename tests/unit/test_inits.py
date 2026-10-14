from unittest.mock import MagicMock

import pytest
from django.core.exceptions import ImproperlyConfigured

from lapidarium.inits import (
    ServiceInjectionMiddleware,
    Services,
    feed_sources,
    newsletter,
)
from lapidarium.links.newsletter.log import LogNewsletter
from lapidarium.links.newsletter.mailchimp import MailchimpNewsletter
from lapidarium.mills.catalogue import CatalogueService
from lapidarium.mills.content import (
    ContentExportService,
    ContentImportService,
    LocalSetupService,
)
from lapidarium.mills.feeds import FeedSyncService
from lapidarium.mills.health import ContentHealthService
from lapidarium.mills.outreach import OutreachService
from lapidarium.mills.schema import SchemaService
from lapidarium.mills.site import SiteService


def test_middleware_attaches_services_and_passes_the_request_on():
    get_response = MagicMock(return_value="response")
    request = MagicMock()

    response = ServiceInjectionMiddleware(get_response)(request)

    assert response == "response"
    get_response.assert_called_once_with(request)
    assert isinstance(request.services, Services)


def test_services_are_built_once_per_container():
    services = Services()

    assert isinstance(services.schema, SchemaService)
    assert isinstance(services.content_export, ContentExportService)
    assert isinstance(services.content_import, ContentImportService)
    assert isinstance(services.local_setup, LocalSetupService)
    first = services.content_import
    assert services.content_import is first
    assert isinstance(services.site, SiteService)
    assert isinstance(services.catalogue, CatalogueService)
    assert isinstance(services.outreach, OutreachService)
    assert isinstance(services.feed_sync, FeedSyncService)
    assert isinstance(services.content_health, ContentHealthService)


@pytest.mark.parametrize(
    ("backend", "expected"),
    (("log", LogNewsletter), ("mailchimp", MailchimpNewsletter)),
)
def test_newsletter_follows_the_setting(*, settings, monkeypatch, backend, expected):
    for name in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy"):
        monkeypatch.delenv(name, raising=False)
    settings.NEWSLETTER_BACKEND = backend
    settings.MAILCHIMP_API_KEY = "key-us1"

    assert isinstance(newsletter(), expected)


def test_feed_sources_come_from_the_setting(settings):
    settings.FEED_SOURCES = [
        "youtube:UC1",
        "github:owner/repo",
        "atom:https://blog.example.com/feed.xml",
    ]

    names = [source.name for source in feed_sources()]

    assert names == [
        "YouTube https://www.youtube.com/feeds/videos.xml?channel_id=UC1",
        "GitHub https://github.com/owner/repo/releases.atom",
        "blog.example.com https://blog.example.com/feed.xml",
    ]


@pytest.mark.parametrize("item", ("vimeo:123", "youtube:", "nonsense"))
def test_unreadable_feed_sources_stop_the_start(settings, item):
    settings.FEED_SOURCES = [item]

    with pytest.raises(ImproperlyConfigured):
        feed_sources()
