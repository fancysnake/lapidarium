import datetime as dt
from http import HTTPStatus

import pytest
from django.db import OperationalError, connection
from django.utils import timezone

from lapidarium.edges.healthcheck import probe_host
from lapidarium.links.db.django.models import Maintenance

pytestmark = pytest.mark.django_db


def _assert_probe(response, *, status, body):
    assert response.status_code == status
    assert response.content == body
    assert response["Content-Type"] == "text/plain"
    assert "no-cache" in response["Cache-Control"]


def test_healthz_answers_ok_while_the_database_answers(client):
    _assert_probe(client.get("/healthz/"), status=HTTPStatus.OK, body=b"ok")


def test_healthz_answers_unavailable_without_the_database(client, monkeypatch):
    def unreachable():
        msg = "connection refused"
        raise OperationalError(msg)

    monkeypatch.setattr(connection, "cursor", unreachable)

    _assert_probe(
        client.get("/healthz/"),
        status=HTTPStatus.SERVICE_UNAVAILABLE,
        body=b"unavailable",
    )


def test_healthz_stays_open_during_maintenance(client):
    now, hour = timezone.now(), dt.timedelta(hours=1)
    Maintenance.objects.create(starts_at=now - hour, ends_at=now + hour, title="Away")

    _assert_probe(client.get("/healthz/"), status=HTTPStatus.OK, body=b"ok")


@pytest.mark.parametrize(
    ("allowed", "host"),
    (
        (["example.com", "www.example.com"], "example.com"),
        ([".example.com"], "example.com"),
        (["*"], "localhost"),
    ),
    ids=("first-entry", "leading-dot", "wildcard"),
)
def test_the_probe_sends_a_host_the_site_allows(*, client, settings, allowed, host):
    settings.ALLOWED_HOSTS = allowed

    assert probe_host(allowed) == host
    _assert_probe(
        client.get("/healthz/", HTTP_HOST=probe_host(allowed)),
        status=HTTPStatus.OK,
        body=b"ok",
    )
