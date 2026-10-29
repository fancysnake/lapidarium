from unittest.mock import MagicMock

import pytest
from django.core.exceptions import ImproperlyConfigured

from lapidarium.inits import (
    Process,
    ServiceInjectionMiddleware,
    Services,
    build_newsletter,
)
from lapidarium.links.newsletter.log import LogNewsletter
from lapidarium.links.newsletter.mailchimp import MailchimpNewsletter
from lapidarium.mills.catalogue import CatalogueService
from lapidarium.mills.content import (
    ContentExportService,
    ContentImportService,
    LocalSetupService,
)
from lapidarium.mills.maintenance import MaintenanceService
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
    assert isinstance(services.maintenance, MaintenanceService)
    assert isinstance(services.catalogue, CatalogueService)
    assert isinstance(services.outreach, OutreachService)


def test_requests_share_one_newsletter(monkeypatch):
    build = MagicMock()
    monkeypatch.setattr("lapidarium.inits.build_newsletter", build)
    monkeypatch.setattr("lapidarium.inits.PROCESS", Process())
    middleware = ServiceInjectionMiddleware(MagicMock())
    first, second = MagicMock(), MagicMock()

    middleware(first)
    middleware(second)

    assert isinstance(first.services.outreach, OutreachService)
    assert isinstance(second.services.outreach, OutreachService)
    build.assert_called_once_with()


def test_requests_share_one_theme():
    assert Services().theme is Services().theme


@pytest.mark.parametrize(
    ("backend", "expected"),
    (("log", LogNewsletter), ("mailchimp", MailchimpNewsletter)),
)
def test_newsletter_follows_the_setting(*, settings, monkeypatch, backend, expected):
    for name in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy"):
        monkeypatch.delenv(name, raising=False)
    settings.NEWSLETTER_BACKEND = backend
    settings.MAILCHIMP_API_KEY = "key-us1"
    settings.MAILCHIMP_LIST_ID = "list"

    assert isinstance(build_newsletter(), expected)


@pytest.mark.parametrize(
    ("backend", "api_key", "list_id"),
    (("mailchump", "", ""), ("mailchimp", "", "list"), ("mailchimp", "key-us1", "")),
)
def test_a_newsletter_that_cannot_work_stops_the_start(
    *, settings, monkeypatch, backend, api_key, list_id
):
    monkeypatch.setattr("lapidarium.inits.PROCESS", Process())
    settings.NEWSLETTER_BACKEND = backend
    settings.MAILCHIMP_API_KEY = api_key
    settings.MAILCHIMP_LIST_ID = list_id

    with pytest.raises(ImproperlyConfigured):
        ServiceInjectionMiddleware(MagicMock())
