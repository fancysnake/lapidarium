from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.management.base import CommandError
from django.utils.module_loading import import_string

if TYPE_CHECKING:
    from collections.abc import Callable, Collection

    from lapidarium.pacts.content import ContentSummaryDTO
    from lapidarium.pacts.services import ServicesProtocol


def build_services() -> ServicesProtocol:
    """Services for a command; nothing dispatches here to attach them."""
    factory: Callable[[], ServicesProtocol] = import_string(settings.SERVICES_FACTORY)
    return factory()


def check_demo(name: str, names: Collection[str]) -> None:
    if name not in names:
        msg = f"Demo {name!r}: not one of {', '.join(names)}."
        raise CommandError(msg)


def counts(summary: ContentSummaryDTO) -> str:
    return f"{summary.types} types, {summary.entries} entries, {summary.assets} assets"
