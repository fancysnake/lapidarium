from unittest.mock import MagicMock

from lapidarium.inits import ServiceInjectionMiddleware, Services
from lapidarium.mills import ContentExportService, ContentImportService, SchemaService


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
    first = services.content_import
    assert services.content_import is first
