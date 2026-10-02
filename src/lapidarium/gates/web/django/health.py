from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.views.decorators.cache import never_cache


@never_cache
@transaction.non_atomic_requests
def healthz(_request: HttpRequest) -> HttpResponse:
    """Liveness probe for the container platform; no database round trip."""
    return HttpResponse("ok", content_type="text/plain")
