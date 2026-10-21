from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from lapidarium.gates.web.django.about import about
from lapidarium.gates.web.django.contact import contact
from lapidarium.gates.web.django.content_health import content_health
from lapidarium.gates.web.django.details import detail
from lapidarium.gates.web.django.feeds import ical_feed, rss
from lapidarium.gates.web.django.health import healthz
from lapidarium.gates.web.django.home import home
from lapidarium.gates.web.django.lists import listing
from lapidarium.gates.web.django.newsletter import newsletter
from lapidarium.gates.web.django.search import search
from lapidarium.gates.web.django.theme_preview import theme_preview
from lapidarium.gates.web.django.whats_new import whats_new

# Fixed pages first: every other first segment is a content type's route.
urlpatterns = [
    path(f"{settings.ADMIN_URL}theme-preview/", theme_preview, name="theme_preview"),
    path(f"{settings.ADMIN_URL}content-health/", content_health, name="content_health"),
    path(settings.ADMIN_URL, admin.site.urls),
    path("healthz/", healthz, name="healthz"),
    path("", home, name="home"),
    path("about/", about, name="about"),
    path("new/", whats_new, name="whats_new"),
    path("search/", search, name="search"),
    path("newsletter/", newsletter, name="newsletter"),
    path("contact/", contact, name="contact"),
    path("rss.xml", rss, name="rss"),
    path("calendar.ics", ical_feed, name="ical"),
    path("<slug:route>/", listing, name="listing"),
    path("<slug:route>/<slug:slug>/", detail, name="detail"),
    # Uploads in development; empty when DEBUG is off.
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]
