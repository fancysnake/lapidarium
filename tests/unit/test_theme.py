from unittest.mock import MagicMock

import pytest

from lapidarium.mills.theme import ThemeService
from lapidarium.pacts import REQUIRED_TOKENS, ProblemLevel, ThemeDTO, ThemeProblem

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
    return ThemeService(store=store, engine_version=engine, static_prefix="themes")


def _codes(problems):
    return [p.code for p in problems]


def test_a_complete_theme_has_no_problems():
    assert _service().check() == []


def test_active_tokens_override_the_base():
    active = _theme("green", tokens={"--color-bg": "#fafafa"})

    service = _service(active=active)

    assert service.background() == "#fafafa"
    assert service.active().key == "green"


def test_each_layer_sets_its_dark_tokens_over_its_own_light_ones():
    # Over the base's dark #000000, --color-text would fail the contrast check.
    base = _theme(tokens=COMPLETE, dark_tokens={"--color-bg": "#000000"})
    active = _theme("x", tokens={"--color-bg": "#fafafa"})

    assert _service(base=base, active=active).check() == []


def test_a_problem_takes_its_level_from_its_code():
    assert ThemeProblem.LOW_CONTRAST.level == ProblemLevel.ERROR
    assert ThemeProblem.STALE_OVERRIDE.level == ProblemLevel.WARNING


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


def test_missing_tokens_are_errors():
    base = _theme(tokens={k: v for k, v in COMPLETE.items() if k != "--gutter"})

    problems = _service(base=base).check()

    assert _codes(problems) == [ThemeProblem.MISSING_REQUIRED]
    assert "--gutter" in problems[0].message


def test_low_contrast_is_an_error():
    active = _theme("pale", tokens={"--color-brand": "#dddddd"})

    problems = _service(active=active).check()

    assert [p.message.split(" has")[0] for p in problems] == [
        "--color-brand on --color-bg (light)",
        "--color-brand-contrast on --color-brand (light)",
    ]


def test_dark_tokens_are_checked_too():
    dark = {"--color-bg": "#111111", "--color-text": "#222222"}
    service = _service(active=_theme("night", dark_tokens=dark))

    problems = service.check()

    assert [p.message.split(" has")[0] for p in problems] == [
        "--color-text on --color-bg (dark)",
        "--color-brand on --color-bg (dark)",
        "--color-type-default on --color-bg (dark)",
    ]


@pytest.mark.parametrize(
    ("declared", "engine", "codes"),
    (
        (None, "0.1.0", [ThemeProblem.NO_ENGINE]),
        ("0.2", "0.1.0", [ThemeProblem.OTHER_ENGINE]),
        ("1.0", "1.4.2", []),
        ("1", "2.0.0", [ThemeProblem.OTHER_ENGINE]),
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

    assert _codes(problems) == [ThemeProblem.STALE_OVERRIDE]
    assert "lapidarium/gone.html" in problems[0].message
