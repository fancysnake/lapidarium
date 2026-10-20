import pytest

from lapidarium.inits import Services


@pytest.fixture(name="media_root")
def media_root_fixture(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    return settings.MEDIA_ROOT


@pytest.fixture(name="layered_theme")
def layered_theme_fixture(tmp_path):
    """Write a theme that loads over the base: fonts, dark tokens, a stylesheet."""
    theme = tmp_path / "themes" / "dusk"
    theme.mkdir(parents=True)
    (theme / "theme.toml").write_text(
        'name = "Dusk"\nversion = "1.0.0"\nengine = "0.1"\n'
        'fonts = ["https://fonts.googleapis.com/css2?family=Gabarito"]\n'
    )
    (theme / "tokens.css").write_text(
        ":root { --color-brand: #0b6b33; --color-link: #0b6b33; }\n"
        "@media (prefers-color-scheme: dark) {\n"
        "  :root { --color-bg: #121412; --color-text: #ecefe9; }\n"
        "}\n"
    )
    (theme / "theme.css").write_text(".card { box-shadow: none; }\n")
    return theme


@pytest.fixture(name="demo")
def demo_fixture(media_root, django_capture_on_commit_callbacks):
    """Load the ttrpg demo, its files under this test's own media root."""
    with django_capture_on_commit_callbacks(execute=True):
        Services().content_import.load_demo("ttrpg")
    return media_root
