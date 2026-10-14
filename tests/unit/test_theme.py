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
    store.base.return_value = base or _theme(tokens=COMPLETE)
    store.active.return_value = active or store.base.return_value
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
    assert service.active() == active


def test_a_background_that_is_not_hex_falls_back_to_white():
    service = _service(active=_theme("x", tokens={"--color-bg": "white"}))

    assert service.background() == "#ffffff"


def test_missing_tokens_are_errors():
    base = _theme(tokens={k: v for k, v in COMPLETE.items() if k != "--gutter"})

    problems = _service(base=base).check()

    assert _codes(problems) == [(ProblemLevel.ERROR, "E001")]
    assert "--gutter" in problems[0].message


def test_low_contrast_is_an_error_and_odd_values_are_skipped():
    active = _theme(
        "pale", tokens={"--color-brand": "#dddddd", "--color-type-default": "var(--x)"}
    )

    problems = _service(active=active).check()

    assert [p.message.split(" has")[0] for p in problems] == [
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
        ("", "0.1.0", [(ProblemLevel.WARNING, "W001")]),
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
