from django.apps import AppConfig


class DbConfig(AppConfig):
    name = "lapidarium.links.db.django"
    label = "lapidarium_db"
    default_auto_field = "django.db.models.BigAutoField"
