from unittest.mock import MagicMock

from lapidarium.inits import ServiceInjectionMiddleware, Services


def test_middleware_attaches_services_and_passes_the_request_on():
    get_response = MagicMock(return_value="response")
    request = MagicMock()

    response = ServiceInjectionMiddleware(get_response)(request)

    assert response == "response"
    get_response.assert_called_once_with(request)
    assert isinstance(request.services, Services)
