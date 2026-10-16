import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

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
        '@import url("fonts.css");\n'
        ":root { --color-bg: #fff; --gutter: 32px }\n"
        ".card { --color-bg: #eee; }\n"
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

    assert (dto.name, dto.version, dto.engine, dto.fonts) == ("bare", None, None, ())
    assert dto.has_stylesheet is False
    assert dto.templates == ()


@pytest.mark.parametrize("css", (":root { --color-bg #fff; }", ":root"))
def test_tokens_that_do_not_parse_name_the_file(*, tmp_path, css):
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "tokens.css").write_text(css)

    with pytest.raises(ImproperlyConfigured, match=r"broken/tokens\.css, line 1"):
        read_theme(tmp_path / "broken")


@pytest.mark.parametrize("name", ("base", "gm-screen"))
def test_shipped_themes_with_the_base_define_every_required_token(name):
    base = read_theme(settings.ENGINE_THEMES / "base")
    theme = read_theme(settings.ENGINE_THEMES / name)

    assert {**base.tokens, **theme.tokens}.keys() >= REQUIRED_TOKENS


def test_store_reads_layers_in_order_and_engine_templates():
    store = ThemeFiles(
        layers=(settings.ENGINE_THEMES / "base", settings.ENGINE_THEMES / "gm-screen"),
        engine_templates=settings.ENGINE_TEMPLATES,
    )

    base, active = store.layers()
    assert (base.key, active.key) == ("base", "gm-screen")
    assert active.dark_tokens["--color-bg"] == "#121412"
    assert "lapidarium/base.html" in store.engine_templates()
