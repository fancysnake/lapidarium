"""In maintenance, visitors meet one page everywhere; signed-in users see the site."""

import datetime as dt
import importlib
from http import HTTPStatus

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model

from lapidarium.links.db.django.models import Entry, Maintenance, Profile
from tests.integration.web.conftest import NOW

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]

HOUR = dt.timedelta(hours=1)
REASONS = ("feeding the mimics", "identifying player tribes")


def _maintenance(**values):
    return Maintenance.objects.create(
        **{
            "starts_at": NOW - HOUR,
            "ends_at": NOW + HOUR,
            "reasons": f"{REASONS[0]}\n\n  {REASONS[1]}  \n",
            **values,
        }
    )


def _detail_path():
    entry = Entry.objects.filter(status="published", type__has_detail_page=True).first()
    assert entry is not None
    return f"/{entry.type.route}/{entry.slug}/"


@pytest.mark.parametrize(
    "path", ("/", "/about/", "/search/?q=e", "/rss.xml", "/no/such-place/")
)
def test_every_page_answers_with_the_maintenance_page(site, path):
    _maintenance()

    response = site.get(path)

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response["Retry-After"] == "3600"
    assert "no-cache" in response["Cache-Control"]
    assert response.templates[0].name == "lapidarium/pages/maintenance.html"
    notice = response.context["notice"]
    profile = Profile.objects.get()
    assert notice.profile is not None
    assert (notice.profile.name, notice.owner_name) == (profile.name, profile.name)
    assert (notice.starts_at, notice.ends_at) == (NOW - HOUR, NOW + HOUR)
    assert notice.reason in REASONS
    assert notice.retry_after == 3600
    assert notice.reason in response.content.decode()


def test_a_detail_page_hides_behind_the_maintenance_page(site):
    _maintenance()

    response = site.get(_detail_path())

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE


def test_without_an_end_or_reasons_the_page_gives_neither(browser):
    _maintenance(ends_at=None, reasons="")

    response = browser.get("/")

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert "Retry-After" not in response
    notice = response.context["notice"]
    assert notice.profile is None
    assert (notice.ends_at, notice.reason, notice.retry_after) == (None, "", None)
    assert "The site is being prepared." in response.content.decode()


def test_signed_in_users_see_the_real_site(site):
    _maintenance()
    site.force_login(get_user_model().objects.create_user("mira", password="pw"))

    assert site.get("/").status_code == HTTPStatus.OK
    assert site.get(_detail_path()).status_code == HTTPStatus.OK


def test_the_admin_health_probe_and_uploads_stay_open(client):
    # The plain client: the admin's own templates leave variables undefined.
    _maintenance(ends_at=None)

    assert client.get("/").status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert client.get("/admin/login/").status_code == HTTPStatus.OK
    assert client.get("/admin").status_code == HTTPStatus.MOVED_PERMANENTLY
    assert client.get("/healthz/").status_code == HTTPStatus.OK
    # Reached the URL resolver: uploads are served only while DEBUG is on.
    assert client.get("/media/assets/none.png").status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize(
    "values",
    ({"enabled": False}, {"starts_at": NOW + HOUR}, {"ends_at": NOW}),
    ids=("off", "not-started", "ended"),
)
def test_outside_its_window_the_site_is_live(site, values):
    _maintenance(**values)

    assert site.get("/").status_code == HTTPStatus.OK


def test_a_new_site_starts_in_maintenance_and_one_with_content_does_not():
    migration = importlib.import_module(
        "lapidarium.links.db.django.migrations.0005_maintenance"
    )

    migration.hide_a_new_site(apps, None)
    assert Maintenance.objects.get().enabled is True

    Maintenance.objects.all().delete()
    Profile.objects.create(name="Mira")
    migration.hide_a_new_site(apps, None)
    assert not Maintenance.objects.exists()
