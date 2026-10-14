"""Themes: assets on every page, the preview, the system checks."""

from http import HTTPStatus

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core import checks

from lapidarium import inits
from lapidarium.gates.web.django.checks import theme_check

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


@pytest.fixture(name="gm_screen")
def gm_screen_fixture(settings, monkeypatch):
    settings.THEME_DIR = settings.ENGINE_THEMES / "gm-screen"
    monkeypatch.setattr(inits, "PROCESS", inits.Process())


@pytest.fixture(name="bare_theme")
def bare_theme_fixture(*, settings, monkeypatch, tmp_path):
    """Use a theme that sets only a brand too pale to read, and no engine."""
    (tmp_path / "bare").mkdir()
    (tmp_path / "bare" / "tokens.css").write_text(":root { --color-brand: #eeeeee; }")
    settings.THEME_DIR = tmp_path / "bare"
    monkeypatch.setattr(inits, "PROCESS", inits.Process())


def test_the_base_theme_loads_its_tokens_only(site):
    response = site.get("/")

    assert response.context["site"].theme.key == "base"
    assert "/static/themes/base/tokens.css" in response.text
    assert "fonts.googleapis.com" not in response.text
    assert "prefers-color-scheme" not in response.text


@pytest.mark.usefixtures("gm_screen")
def test_another_theme_loads_over_the_base(site):
    response = site.get("/")

    text = response.text
    assert response.context["site"].theme.key == "gm-screen"
    assert "fonts.googleapis.com/css2?family=Spectral" in text
    assert text.index("themes/base/tokens.css") < text.index(
        "themes/gm-screen/tokens.css"
    )
    assert "/static/themes/gm-screen/theme.css" in text
    assert "@media (prefers-color-scheme: dark)" in text


def test_the_preview_is_for_staff(site):
    response = site.get("/admin/theme-preview/")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"].startswith("/admin/login/")


def test_the_preview_shows_components_and_checks(site):
    user = get_user_model().objects.create_superuser("curator", password="pw")
    site.force_login(user)

    response = site.get("/admin/theme-preview/")

    assert response.status_code == HTTPStatus.OK
    assert response.context["problems"] == ()
    assert len(response.context["home"].doors) == 5
    assert "The theme meets the contract." in response.text
    assert 'class="door"' in response.text


@pytest.mark.usefixtures("bare_theme")
def test_the_preview_lists_problems(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.get("/admin/theme-preview/")

    assert [p.code for p in response.context["problems"]] == ["E002", "E002", "W001"]
    assert "W001" in response.text


@pytest.mark.usefixtures("bare_theme")
def test_system_checks_report_the_theme():

    messages = theme_check(None)

    assert [(type(m), m.id) for m in messages] == [
        (checks.Error, "lapidarium.E002"),
        (checks.Error, "lapidarium.E002"),
        (checks.Warning, "lapidarium.W001"),
    ]


def test_system_checks_skip_other_apps():
    assert theme_check([apps.get_app_config("auth")]) == []
    assert theme_check([apps.get_app_config("lapidarium_web")]) == []
