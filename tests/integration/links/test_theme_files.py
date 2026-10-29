import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from lapidarium.links.themes.files import ThemeFiles, read_theme
from lapidarium.pacts.theme import REQUIRED_TOKENS


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
        ":root { color: black; --color-bg: #ffffff; --gutter: 32px }\n"
        ".card { --color-bg: #eeeeee; }\n"
        "@media (max-width: 40rem) { :root { --gutter: 16px; } }\n"
        "@media (prefers-color-scheme: dark) { :root { --color-bg: #111111; } }\n"
    )

    dto = read_theme(theme, href="themes/night")

    assert dto.key == "night"
    assert (dto.name, dto.version, dto.engine) == ("Night", "2.0", "0.1")
    assert dto.fonts == ("https://f",)
    assert dto.tokens_href == "themes/night/tokens.css"
    assert dto.stylesheet_href == "themes/night/theme.css"
    assert dto.tokens == {"--color-bg": "#ffffff", "--gutter": "32px"}
    assert dto.dark_tokens == {"--color-bg": "#111111"}
    assert dto.templates == ("lapidarium/base.html",)


def test_a_bare_theme_needs_only_tokens(tmp_path):
    (tmp_path / "bare").mkdir()
    (tmp_path / "bare" / "tokens.css").write_text(":root { --color-bg: #ffffff; }")

    dto = read_theme(tmp_path / "bare", href="themes/bare")

    assert (dto.name, dto.version, dto.engine, dto.fonts) == ("bare", None, None, ())
    assert dto.stylesheet_href is None
    assert dto.templates == ()


@pytest.mark.parametrize("css", (":root { --color-bg #fff; }", ":root"))
def test_tokens_that_do_not_parse_name_the_file(*, tmp_path, css):
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "tokens.css").write_text(css)

    with pytest.raises(ImproperlyConfigured, match=r"broken/tokens\.css, line 1"):
        read_theme(tmp_path / "broken", href="themes/broken")


def test_errors_inside_a_block_count_lines_from_the_top_of_the_file(tmp_path):
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "tokens.css").write_text(
        ":root { --color-bg: #ffffff; }\n"
        "@media (prefers-color-scheme: dark) {\n"
        "  :root {\n"
        "    --color-bg #111;\n"
        "  }\n"
        "}\n"
    )

    with pytest.raises(ImproperlyConfigured, match=r"broken/tokens\.css, line 4"):
        read_theme(tmp_path / "broken", href="themes/broken")


@pytest.mark.parametrize(
    "css",
    (
        ":root { --gutter: 4px; }\n:root { --color-bg: white; }",
        (
            ":root { --gutter: 4px; }\n"
            "@media (prefers-color-scheme: dark) { :root { --color-text: #eee; } }"
        ),
    ),
)
def test_colours_the_contrast_check_reads_must_be_rrggbb(*, tmp_path, css):
    (tmp_path / "soft").mkdir()
    (tmp_path / "soft" / "tokens.css").write_text(css)

    with pytest.raises(
        ImproperlyConfigured, match=r"soft/tokens\.css, line 2: --color-.* #rrggbb"
    ):
        read_theme(tmp_path / "soft", href="themes/soft")


def test_the_base_theme_defines_every_required_token():
    base = read_theme(settings.ENGINE_THEMES / "base", href="themes/base")

    assert base.tokens.keys() >= REQUIRED_TOKENS


def test_store_reads_layers_in_order_and_engine_templates(layered_theme):
    store = ThemeFiles(
        layers=(
            ("assets/base", settings.ENGINE_THEMES / "base"),
            ("assets/dusk", layered_theme),
        ),
        engine_templates=settings.ENGINE_TEMPLATES,
    )

    base, active = store.layers()
    assert (base.key, active.key) == ("base", "dusk")
    assert active.tokens_href == "assets/dusk/tokens.css"
    assert active.dark_tokens["--color-bg"] == "#121412"
    assert "lapidarium/base.html" in store.engine_templates()
