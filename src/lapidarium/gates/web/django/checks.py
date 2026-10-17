"""System checks: the active theme against the theme contract, at every start."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.core import checks
from django.utils.module_loading import import_string

from lapidarium.pacts import ProblemLevel

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from django.apps import AppConfig

    from lapidarium.pacts import ServicesProtocol


def theme_check(
    app_configs: Sequence[AppConfig] | None, **_kwargs: Sequence[str] | bool | None
) -> list[checks.CheckMessage]:
    if app_configs is not None and all(
        config.label != "lapidarium_web" for config in app_configs
    ):
        return []
    # Checks run outside any request, so nothing has attached the services.
    factory: Callable[[], ServicesProtocol] = import_string(settings.SERVICES_FACTORY)
    return [
        (checks.Error if p.code.level == ProblemLevel.ERROR else checks.Warning)(
            p.message, id=f"lapidarium.{p.code}"
        )
        for p in factory().theme.check()
    ]
