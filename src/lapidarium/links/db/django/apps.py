from django.apps import AppConfig

from lapidarium.links.db.django import signals


class DbConfig(AppConfig):
    name = "lapidarium.links.db.django"
    label = "lapidarium_db"

    def ready(self) -> None:
        signals.connect(self.label)
