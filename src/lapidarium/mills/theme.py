"""The active theme against its contract: tokens, engine, overrides, contrast."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from lapidarium.mills.colour import WHITE, contrast_ratio, lowest_contrast, tint_over
from lapidarium.pacts.services import ThemeServiceProtocol
from lapidarium.pacts.theme import (
    CONTRAST_PAIRS,
    REQUIRED_TOKENS,
    ProblemDTO,
    SchemeColoursDTO,
    SiteThemeDTO,
    StylesheetDTO,
    ThemeProblem,
)
from lapidarium.specs import CONTRAST_FLOOR

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from lapidarium.pacts.theme import ThemeDTO, ThemeStoreProtocol

_ENGINE_STYLESHEET = "lapidarium/css/base.css"
_BACKGROUND = "--color-bg"
_SURFACE = "--color-surface"


def _release(version: str) -> tuple[str, ...]:
    """Return the part of a version that must match: major, or 0.minor before 1.0."""
    parts = version.split(".")
    return tuple(parts[:2]) if parts[0] == "0" else tuple(parts[:1])


def _contrast_problems(
    tokens: Mapping[str, str], *, scheme: str
) -> Iterator[ProblemDTO]:
    checked: set[tuple[str, str]] = set()
    for text, background in CONTRAST_PAIRS:
        if text not in tokens or background not in tokens:
            continue
        if (text, tokens[background]) in checked:
            continue
        checked.add((text, tokens[background]))
        if (ratio := contrast_ratio(tokens[text], tokens[background])) < CONTRAST_FLOOR:
            yield ProblemDTO(
                code=ThemeProblem.LOW_CONTRAST,
                message=(
                    f"{text} on {background} ({scheme}) has contrast"
                    f" {ratio:.2f}:1, needs {CONTRAST_FLOOR}:1."
                ),
            )


def _white_problems(
    token: str, *, light: str, dark: str, drawn_on: tuple[str, ...], what: str
) -> Iterator[ProblemDTO]:
    """Report a dark `token` that white, the lightest type colour, cannot read on.

    A dark colour no darker than its light counterpart lightens none of them.
    `drawn_on` is every colour white lands on there; `what` names them.
    """
    if contrast_ratio(WHITE, dark) <= contrast_ratio(WHITE, light):
        return
    if (ratio := lowest_contrast(WHITE, drawn_on)) >= CONTRAST_FLOOR:
        return
    yield ProblemDTO(
        code=ThemeProblem.LOW_CONTRAST,
        message=(
            f"No type colour reads on {token} (dark): white has"
            f" contrast {ratio:.2f}:1 with {what}, needs {CONTRAST_FLOOR}:1."
        ),
    )


def _type_colour_problems(
    light: SchemeColoursDTO, dark: SchemeColoursDTO
) -> Iterator[ProblemDTO]:
    yield from _white_problems(
        _BACKGROUND,
        light=light.background,
        dark=dark.background,
        drawn_on=(dark.background, tint_over(WHITE, dark.background)),
        what="it or its tint",
    )
    background_covers_surface = dark.surface == dark.background and contrast_ratio(
        WHITE, dark.background
    ) > contrast_ratio(WHITE, light.background)
    if not background_covers_surface:
        yield from _white_problems(
            _SURFACE,
            light=light.surface,
            dark=dark.surface,
            drawn_on=(dark.surface,),
            what="it",
        )


def _scheme(tokens: Mapping[str, str]) -> SchemeColoursDTO:
    return SchemeColoursDTO(background=tokens[_BACKGROUND], surface=tokens[_SURFACE])


def _site_theme(layers: tuple[ThemeDTO, ...]) -> SiteThemeDTO:
    fonts = [url for layer in layers for url in layer.fonts]
    paths = [
        *(layer.tokens_href for layer in layers),
        _ENGINE_STYLESHEET,
        *(layer.stylesheet_href for layer in layers if layer.stylesheet_href),
    ]
    active = layers[-1]
    return SiteThemeDTO(
        key=active.key,
        name=active.name,
        version=active.version,
        stylesheets=(
            *(StylesheetDTO(href=url, external=True) for url in fonts),
            *(StylesheetDTO(href=path, external=False) for path in paths),
        ),
    )


class ThemeService(ThemeServiceProtocol):
    """Read through `store`; checked against `engine_version`.

    `ValueError` when no layer sets `--color-bg` or `--color-surface`: the colour
    checks need them.
    """

    def __init__(self, *, store: ThemeStoreProtocol, engine_version: str) -> None:
        self._store = store
        self._engine_version = engine_version
        self._layers = store.layers()
        # What the page sees: each layer's tokens over the one before, and in the
        # dark scheme each layer's dark tokens over its own light ones.
        self._light: dict[str, str] = {}
        self._dark: dict[str, str] = {}
        for layer in self._layers:
            self._light |= layer.tokens
            self._dark |= layer.tokens | layer.dark_tokens
        for token in (_BACKGROUND, _SURFACE):
            if token not in self._light:
                msg = f"No theme defines the required token {token}."
                raise ValueError(msg)
        self._has_dark = any(layer.dark_tokens for layer in self._layers)
        self._active = _site_theme(self._layers)

    @override
    def active(self) -> SiteThemeDTO:
        return self._active

    @override
    def colours(self) -> SchemeColoursDTO:
        return _scheme(self._light)

    @override
    def dark_colours(self) -> SchemeColoursDTO | None:
        return _scheme(self._dark) if self._has_dark else None

    @override
    def check(self) -> list[ProblemDTO]:
        return [
            *self._missing_tokens(),
            *self._contrast(),
            *self._engine(),
            *self._stale_overrides(),
        ]

    def _missing_tokens(self) -> Iterator[ProblemDTO]:
        for token in sorted(REQUIRED_TOKENS - self._light.keys()):
            yield ProblemDTO(
                code=ThemeProblem.MISSING_REQUIRED,
                message=f"No theme defines the required token {token}.",
            )

    def _contrast(self) -> Iterator[ProblemDTO]:
        yield from _contrast_problems(self._light, scheme="light")
        if self._has_dark:
            yield from _contrast_problems(self._dark, scheme="dark")
            yield from _type_colour_problems(self.colours(), _scheme(self._dark))

    def _engine(self) -> Iterator[ProblemDTO]:
        active = self._layers[-1]
        if active.engine is None:
            yield ProblemDTO(
                code=ThemeProblem.NO_ENGINE,
                message=f"Theme {active.key!r} declares no engine version.",
            )
        elif _release(active.engine) != _release(self._engine_version):
            yield ProblemDTO(
                code=ThemeProblem.OTHER_ENGINE,
                message=(
                    f"Theme {active.key!r} is built for engine {active.engine};"
                    f" this is {self._engine_version}."
                ),
            )

    def _stale_overrides(self) -> Iterator[ProblemDTO]:
        engine_templates = self._store.engine_templates()
        for path in sorted(set(self._layers[-1].templates) - engine_templates):
            yield ProblemDTO(
                code=ThemeProblem.STALE_OVERRIDE,
                message=f"Theme overrides {path}, which the engine no longer has.",
            )
