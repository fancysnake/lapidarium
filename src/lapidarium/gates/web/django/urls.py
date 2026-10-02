from django.conf import settings
from django.contrib import admin
from django.urls import path

from lapidarium.gates.web.django.health import healthz

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("healthz/", healthz, name="healthz"),
]
