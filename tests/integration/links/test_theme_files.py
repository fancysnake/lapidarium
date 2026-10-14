import pytest
from django.conf import settings

from lapidarium.links.themes.files import ThemeFiles, read_theme
from lapidarium.pacts import REQUIRED_TOKENS


def test_reads_manifest_tokens_dark_tokens_and_templates(tmp_path):
    theme = tmp_path / "night"
    (theme / "templates" / "lapidarium").mkdir(parents=True)
    (theme / "templates" / "lapidarium" / "base.html").write_text("")
    (theme / "theme.toml").write_text(
        'name = "Night"\nversion = "2.0"\nengine = "0.1"\nfonts = ["https://f"]\n'
    )
    (theme / "theme.css").write_text("")
    (theme / "tokens.css").write_text(
        "/* --color-skip: #000; */\n"
        ":root { --color-bg: #fff; --gutter: 32px }\n"
        "@media (max-width: 40rem) { :root { --gutter: 16px; } }\n"
        "@media (prefers-color-scheme: dark) { :root { --color-bg: #111; } }\n"
    )

    dto = read_theme(theme)

    assert dto.key == "night"
    assert (dto.name, dto.version, dto.engine) == ("Night", "2.0", "0.1")
    assert dto.fonts == ("https://f",)
    assert dto.has_stylesheet is True
    assert dto.tokens == {"--color-bg": "#fff", "--gutter": "32px"}
    assert dto.dark_tokens == {"--color-bg": "#111"}
    assert dto.templates == ("lapidarium/base.html",)


def test_a_bare_theme_needs_only_tokens(tmp_path):
    (tmp_path / "bare").mkdir()
    (tmp_path / "bare" / "tokens.css").write_text(":root { --color-bg: #fff; }")

    dto = read_theme(tmp_path / "bare")

    assert (dto.name, dto.version, dto.engine, dto.fonts) == ("bare", "", "", ())
    assert dto.has_stylesheet is False
    assert dto.templates == ()


@pytest.mark.parametrize("name", ("base", "gm-screen"))
def test_shipped_themes_with_the_base_define_every_required_token(name):
    base = read_theme(settings.BASE_THEME_DIR)
    theme = read_theme(settings.ENGINE_THEMES / name)

    assert {**base.tokens, **theme.tokens}.keys() >= REQUIRED_TOKENS


def test_store_reads_base_active_and_engine_templates():
    store = ThemeFiles(
        base=settings.BASE_THEME_DIR,
        active=settings.ENGINE_THEMES / "gm-screen",
        engine_templates=settings.ENGINE_TEMPLATES,
    )

    assert store.base().key == "base"
    assert store.active().key == "gm-screen"
    assert store.active().dark_tokens["--color-bg"] == "#121412"
    assert "lapidarium/base.html" in store.engine_templates()


def test_store_with_the_base_active_reads_it_once():
    store = ThemeFiles(
        base=settings.BASE_THEME_DIR,
        active=settings.BASE_THEME_DIR,
        engine_templates=settings.ENGINE_TEMPLATES,
    )

    assert store.active() is store.base()
