"""Themes: assets on every page, the preview, the system checks."""

from http import HTTPStatus

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core import checks

from lapidarium import inits
from lapidarium.gates.web.django.checks import theme_check

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


@pytest.fixture(name="dusk")
def dusk_fixture(*, settings, monkeypatch, layered_theme):
    settings.THEME_LAYERS = (settings.ENGINE_THEMES / "base", layered_theme)
    monkeypatch.setattr(inits, "PROCESS", inits.Process())


@pytest.fixture(name="bare_theme")
def bare_theme_fixture(*, settings, monkeypatch, tmp_path):
    """Use a theme that sets only a brand too pale to read, and no engine."""
    (tmp_path / "bare").mkdir()
    (tmp_path / "bare" / "tokens.css").write_text(":root { --color-brand: #eeeeee; }")
    settings.THEME_LAYERS = (settings.ENGINE_THEMES / "base", tmp_path / "bare")
    monkeypatch.setattr(inits, "PROCESS", inits.Process())


def test_the_base_theme_loads_its_tokens_only(site):
    response = site.get("/")

    assert "/static/themes/base/tokens.css" in response.text
    assert "fonts.googleapis.com" not in response.text


def test_type_tints_mix_over_the_background_unless_set_for_the_light_scheme(site):
    response = site.get("/")

    text = response.text
    session = next(t for t in response.context["site"].types if t.key == "session")
    mixed = "--type-tint: color-mix(in srgb, var(--type-color) 12%, var(--color-bg));"
    set_tint = f'[data-type="session"] {{ --type-tint: {session.tint}; }}'
    assert (
        f'[data-type="session"] {{ --type-color: {session.colour}; {mixed} }}' in text
    )
    assert text.index("@media (prefers-color-scheme: light)") < text.index(set_tint)


@pytest.mark.usefixtures("dusk")
def test_another_theme_loads_over_the_base(site):
    response = site.get("/")

    text = response.text
    assert "fonts.googleapis.com/css2?family=Gabarito" in text
    assert text.index("themes/base/tokens.css") < text.index("themes/dusk/tokens.css")
    assert "/static/themes/dusk/theme.css" in text


@pytest.mark.usefixtures("dusk")
def test_the_not_found_page_wears_the_theme(site):
    response = site.get("/nope/")

    text = response.text
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "fonts.googleapis.com/css2?family=Gabarito" in text
    assert text.index("themes/base/tokens.css") < text.index("themes/dusk/tokens.css")
    assert "/static/lapidarium/css/base.css" in text
    assert "/static/themes/dusk/theme.css" in text


def test_the_preview_is_for_staff(site):
    response = site.get("/admin/theme-preview/")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"].startswith("/admin/login/")


def test_the_preview_shows_components_and_checks(site):
    user = get_user_model().objects.create_superuser("curator", password="pw")
    site.force_login(user)

    response = site.get("/admin/theme-preview/")

    assert response.status_code == HTTPStatus.OK
    assert response.context["theme"].key == "base"
    assert response.context["problems"] == ()
    assert len(response.context["home"].doors) == 5
    assert "The theme meets the contract." in response.text
    assert 'class="door"' in response.text
    assert 'id="contact-email"' in response.text


@pytest.mark.usefixtures("bare_theme")
def test_the_preview_lists_problems(site):
    site.force_login(get_user_model().objects.create_superuser("c", password="pw"))

    response = site.get("/admin/theme-preview/")

    assert [p.code for p in response.context["problems"]] == ["E002", "E002", "W001"]
    assert "W001" in response.text
    assert "bare (bare)</p>" in response.text


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
