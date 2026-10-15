"""The admin's content health page and dashboard (Unfold templates, not strict)."""

from http import HTTPStatus

import pytest

pytestmark = pytest.mark.django_db


@pytest.mark.usefixtures("demo")
def test_the_admin_page_lists_issues(admin_client):
    response = admin_client.get("/admin/content-health/")

    assert response.status_code == HTTPStatus.OK
    codes = [issue.code for issue in response.context["issues"]]
    assert codes[0] == "H002"
    assert "copernicon-2026" in response.text


@pytest.mark.usefixtures("demo")
def test_the_dashboard_summarises_them(admin_client):
    response = admin_client.get("/admin/")

    assert response.status_code == HTTPStatus.OK
    assert 'href="/admin/content-health/"' in response.text
    assert "event/copernicon-2026" in response.text


def test_nothing_to_look_at(admin_client):
    response = admin_client.get("/admin/content-health/")

    assert response.context["issues"] == []
    assert "Nothing to look at." in response.text
