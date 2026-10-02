from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_admin_login_page_renders_with_unfold(client):
    response = client.get("/admin/login/")

    assert response.status_code == HTTPStatus.OK
    assert "unfold" in response.content.decode()


@pytest.mark.django_db
def test_admin_index_opens_for_staff(client, settings):
    user = get_user_model().objects.create_user("curator", password="pw", is_staff=True)
    client.force_login(user)

    response = client.get("/admin/")

    assert response.status_code == HTTPStatus.OK
    assert settings.SITE_NAME in response.content.decode()
