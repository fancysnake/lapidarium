from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.utils.module_loading import import_string

if TYPE_CHECKING:
    from collections.abc import Callable

    from lapidarium.pacts import ServicesProtocol


def build_services() -> ServicesProtocol:
    """Services for a command; nothing dispatches here to attach them."""
    factory: Callable[[], ServicesProtocol] = import_string(settings.SERVICES_FACTORY)
    return factory()
