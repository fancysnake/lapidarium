import datetime as dt
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from lapidarium.links.db.django.models import Maintenance, Profile

MAINTENANCE = "/admin/lapidarium_db/maintenance/"

pytestmark = pytest.mark.django_db


def test_admin_login_page_renders_with_unfold(client):
    response = client.get("/admin/login/")

    assert response.status_code == HTTPStatus.OK
    assert "unfold" in response.content.decode()


def test_admin_index_opens_for_staff(client, settings):
    user = get_user_model().objects.create_user("curator", password="pw", is_staff=True)
    client.force_login(user)

    response = client.get("/admin/")

    assert response.status_code == HTTPStatus.OK
    assert settings.SITE_NAME in response.content.decode()


@pytest.mark.usefixtures("demo")
def test_profile_is_a_singleton(admin):
    response = admin.get("/admin/lapidarium_db/profile/add/")

    assert response.status_code == HTTPStatus.FORBIDDEN
    Profile.objects.all().delete()
    assert admin.get("/admin/lapidarium_db/profile/add/").status_code == HTTPStatus.OK


def test_maintenance_is_a_singleton(admin):
    assert admin.get(f"{MAINTENANCE}add/").status_code == HTTPStatus.OK
    Maintenance.objects.create()
    assert admin.get(f"{MAINTENANCE}add/").status_code == HTTPStatus.FORBIDDEN


def test_maintenance_turns_off_and_back_on_from_the_list(admin):
    since = timezone.now() - dt.timedelta(days=1)
    maintenance = Maintenance.objects.create(starts_at=since)
    selected = {"_selected_action": [maintenance.pk]}

    response = admin.post(MAINTENANCE, {"action": "turn_off", **selected}, follow=True)

    assert [str(m) for m in response.context["messages"]] == ["The site is live."]
    maintenance.refresh_from_db()
    assert maintenance.ends_at is not None
    assert maintenance.ends_at > since

    response = admin.post(MAINTENANCE, {"action": "turn_on", **selected}, follow=True)

    assert [str(m) for m in response.context["messages"]] == [
        "Visitors now see the maintenance page."
    ]
    maintenance.refresh_from_db()
    assert maintenance.starts_at > since
    assert maintenance.ends_at is None


@pytest.mark.usefixtures("demo")
@pytest.mark.parametrize(
    "model",
    ("mediaasset", "tag", "link", "externalitem", "entrytype", "entry", "maintenance"),
)
def test_changelists_render(admin, model):
    response = admin.get(f"/admin/lapidarium_db/{model}/")

    assert response.status_code == HTTPStatus.OK
