from unittest.mock import MagicMock

import pytest

from lapidarium.mills.theme import ThemeService
from lapidarium.pacts import REQUIRED_TOKENS, ProblemLevel, ThemeDTO

COMPLETE = dict.fromkeys(REQUIRED_TOKENS, "1rem") | {
    "--color-bg": "#ffffff",
    "--color-text": "#151515",
    "--color-brand": "#151515",
    "--color-brand-contrast": "#ffffff",
    "--color-type-default": "#151515",
    "--color-type-default-tint": "#f1f1ee",
}


def _theme(key="base", **overrides):
    return ThemeDTO(
        **{
            "key": key,
            "name": key.title(),
            "version": "1.0.0",
            "engine": "0.1",
            "fonts": (),
            "has_stylesheet": False,
            "tokens": {},
            "dark_tokens": {},
            "templates": (),
            **overrides,
        }
    )


def _service(*, base=None, active=None, engine="0.1.0", templates=frozenset()):
    store = MagicMock()
    base = base or _theme(tokens=COMPLETE)
    store.layers.return_value = (base, active) if active else (base,)
    store.engine_templates.return_value = templates
    return ThemeService(store=store, engine_version=engine)


def _codes(problems):
    return [(p.level, p.code) for p in problems]


def test_a_complete_theme_has_no_problems():
    assert _service().check() == []


def test_active_tokens_override_the_base():
    active = _theme("green", tokens={"--color-bg": "#fafafa"})

    service = _service(active=active)

    assert service.background() == "#fafafa"
    assert service.active().key == "green"


def test_each_layer_sets_its_dark_tokens_over_its_own_light_ones():
    base = _theme(tokens=COMPLETE, dark_tokens={"--color-bg": "#000000"})
    active = _theme("x", tokens={"--color-bg": "#fafafa"})

    service = _service(base=base, active=active)

    assert service.dark_background() == "#fafafa"


def test_the_page_loads_fonts_then_tokens_then_engine_css_then_theme_css():
    base = _theme(tokens=COMPLETE, fonts=("https://base",))
    active = _theme(
        "x", name="X", version="2.0", fonts=("https://x",), has_stylesheet=True
    )

    theme = _service(base=base, active=active).active()

    assert (theme.key, theme.name, theme.version) == ("x", "X", "2.0")
    assert [(s.href, s.external) for s in theme.stylesheets] == [
        ("https://base", True),
        ("https://x", True),
        ("themes/base/tokens.css", False),
        ("themes/x/tokens.css", False),
        ("lapidarium/css/base.css", False),
        ("themes/x/theme.css", False),
    ]


def test_the_base_alone_loads_once():
    theme = _service().active()

    assert [s.href for s in theme.stylesheets] == [
        "themes/base/tokens.css",
        "lapidarium/css/base.css",
    ]


def test_a_background_that_is_not_hex_falls_back_to_white_and_is_an_error():
    service = _service(active=_theme("x", tokens={"--color-bg": "white"}))

    assert service.background() == "#ffffff"
    assert [p.message for p in service.check()] == [
        "--color-bg (light) is 'white'; the contrast check needs #rrggbb."
    ]


def test_a_dark_background_that_is_not_hex_drops_the_dark_scheme():
    dark = {"--color-bg": "rgb(0 0 0)"}
    service = _service(active=_theme("x", dark_tokens=dark))

    assert service.dark_background() is None
    assert _codes(service.check()) == [(ProblemLevel.ERROR, "E003")]


def test_missing_tokens_are_errors():
    base = _theme(tokens={k: v for k, v in COMPLETE.items() if k != "--gutter"})

    problems = _service(base=base).check()

    assert _codes(problems) == [(ProblemLevel.ERROR, "E001")]
    assert "--gutter" in problems[0].message


def test_low_contrast_and_colours_that_are_not_hex_are_errors():
    active = _theme(
        "pale", tokens={"--color-brand": "#dddddd", "--color-type-default": "var(--x)"}
    )

    problems = _service(active=active).check()

    assert [p.message.split(" has")[0] for p in problems] == [
        "--color-type-default (light) is 'var(--x)'; the contrast check needs #rrggbb.",
        "--color-brand on --color-bg (light)",
        "--color-brand-contrast on --color-brand (light)",
    ]


def test_dark_tokens_are_checked_too():
    dark = {"--color-bg": "#111111", "--color-text": "#222222"}
    service = _service(active=_theme("night", dark_tokens=dark))

    problems = service.check()

    assert service.dark_background() == "#111111"
    assert [p.message.split(" has")[0] for p in problems] == [
        "--color-text on --color-bg (dark)",
        "--color-brand on --color-bg (dark)",
        "--color-type-default on --color-bg (dark)",
    ]


def test_no_dark_background_without_dark_tokens():
    assert _service().dark_background() is None


@pytest.mark.parametrize(
    ("declared", "engine", "codes"),
    (
        (None, "0.1.0", [(ProblemLevel.WARNING, "W001")]),
        ("0.2", "0.1.0", [(ProblemLevel.WARNING, "W002")]),
        ("1.0", "1.4.2", []),
        ("1", "2.0.0", [(ProblemLevel.WARNING, "W002")]),
    ),
)
def test_engine_versions(*, declared, engine, codes):
    active = _theme("x", engine=declared)

    assert _codes(_service(active=active, engine=engine).check()) == codes


def test_overrides_of_templates_the_engine_lacks_are_warnings():
    active = _theme("x", templates=("lapidarium/base.html", "lapidarium/gone.html"))

    problems = _service(
        active=active, templates=frozenset({"lapidarium/base.html"})
    ).check()

    assert _codes(problems) == [(ProblemLevel.WARNING, "W003")]
    assert "lapidarium/gone.html" in problems[0].message
