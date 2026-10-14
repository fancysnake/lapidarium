from unittest.mock import MagicMock

import pytest

from lapidarium.inits import ServiceInjectionMiddleware, Services, newsletter
from lapidarium.links.newsletter.log import LogNewsletter
from lapidarium.links.newsletter.mailchimp import MailchimpNewsletter
from lapidarium.mills.catalogue import CatalogueService
from lapidarium.mills.content import (
    ContentExportService,
    ContentImportService,
    LocalSetupService,
)
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
