from typing import override

from django.apps import AppConfig
from django.core import checks

from lapidarium.gates.web.django.checks import theme_check


class WebGatesConfig(AppConfig):
    name = "lapidarium.gates.web.django"
    label = "lapidarium_web"

    @override
    def ready(self) -> None:
        checks.register(theme_check)
