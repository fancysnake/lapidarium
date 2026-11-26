"""The content panel's Site page: staff edit the profile's texts."""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model

from lapidarium.links.db.django.models import Profile

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


_PROFILE = {
    "name": "Mira K.",
    "handle": "@mira",
    "tagline": "Games and songs.",
    "bio": "Hello.",
    "email": "",
    "friends_title": "Znajomi",
    "friends_intro": "",
}


def test_the_site_page_is_for_staff(site):
    response = site.get("/panel/site/")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"].startswith("/admin/login/")


def test_the_site_page_opens_on_the_profile(site):
    site.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )
    profile = Profile.objects.get()

    response = site.get("/panel/site/")

    assert response.status_code == HTTPStatus.OK
    assert response.context["saved"] is False
    assert response.context["form"].initial == {
        "name": profile.name,
        "handle": profile.handle,
        "tagline": profile.tagline,
        "bio": profile.bio,
        "email": profile.email,
        "friends_title": profile.friends_title,
        "friends_intro": profile.friends_intro,
    }
    assert 'aria-current="page">Site</a>' in response.text
    assert ">Admin</a>" not in response.text


def test_the_site_page_of_an_empty_site_opens_blank(browser):
    browser.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = browser.get("/panel/site/")

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].initial == {}
    assert '<a href="/admin/">Admin</a>' in response.text


def test_the_site_page_saves_the_texts_and_keeps_the_photo(site):
    site.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )
    before = Profile.objects.get()

    response = site.post("/panel/site/", _PROFILE)

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"] == "/panel/site/?saved=1"
    after = Profile.objects.get()
    assert {key: getattr(after, key) for key in _PROFILE} == _PROFILE
    assert (after.photo_id, after.button_id) == (before.photo_id, before.button_id)
    saved = site.get(response["Location"])
    assert saved.context["saved"] is True
    assert "The profile is saved." in saved.text
    assert "Mira K." in site.get("/about/").text


def test_the_site_page_keeps_the_form_when_it_cannot_read_it(site):
    site.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )
    name = Profile.objects.get().name

    response = site.post("/panel/site/", {**_PROFILE, "name": "", "email": "nope"})

    assert response.status_code == HTTPStatus.OK
    assert set(response.context["form"].errors) == {"name", "email"}
    assert Profile.objects.get().name == name


def test_the_site_page_refuses_an_email_too_long_to_store(site):
    site.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )
    email = Profile.objects.get().email
    too_long = "a" * 243 + "@example.com"

    response = site.post("/panel/site/", {**_PROFILE, "email": too_long})

    assert response.status_code == HTTPStatus.OK
    assert set(response.context["form"].errors) == {"email"}
    assert Profile.objects.get().email == email
