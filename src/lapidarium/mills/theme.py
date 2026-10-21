"""The active theme against its contract: tokens, engine, overrides, contrast."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from lapidarium.mills.colour import contrast_ratio
from lapidarium.pacts.services import ThemeServiceProtocol
from lapidarium.pacts.theme import (
    CONTRAST_PAIRS,
    REQUIRED_TOKENS,
    ProblemDTO,
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


def _release(version: str) -> tuple[str, ...]:
    """Return the part of a version that must match: major, or 0.minor before 1.0."""
    parts = version.split(".")
    return tuple(parts[:2]) if parts[0] == "0" else tuple(parts[:1])


def _contrast_problems(
    tokens: Mapping[str, str], *, scheme: str
) -> Iterator[ProblemDTO]:
    for text, background in CONTRAST_PAIRS:
        if text not in tokens or background not in tokens:
            continue
        if (ratio := contrast_ratio(tokens[text], tokens[background])) < CONTRAST_FLOOR:
            yield ProblemDTO(
                code=ThemeProblem.LOW_CONTRAST,
                message=(
                    f"{text} on {background} ({scheme}) has contrast"
                    f" {ratio:.2f}:1, needs {CONTRAST_FLOOR}:1."
                ),
            )


def _site_theme(layers: tuple[ThemeDTO, ...], *, static_prefix: str) -> SiteThemeDTO:
    fonts = [url for layer in layers for url in layer.fonts]
    paths = [
        *(f"{static_prefix}/{layer.key}/tokens.css" for layer in layers),
        _ENGINE_STYLESHEET,
        *(
            f"{static_prefix}/{layer.key}/theme.css"
            for layer in layers
            if layer.has_stylesheet
        ),
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

    Each layer's static files are served under `static_prefix`/<key>.
    `ValueError` when no layer sets `--color-bg`: the colour checks need it.
    """

    def __init__(
        self, *, store: ThemeStoreProtocol, engine_version: str, static_prefix: str
    ) -> None:
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
        if _BACKGROUND not in self._light:
            msg = f"No theme defines the required token {_BACKGROUND}."
            raise ValueError(msg)
        self._has_dark = any(layer.dark_tokens for layer in self._layers)
        self._active = _site_theme(self._layers, static_prefix=static_prefix)

    @override
    def active(self) -> SiteThemeDTO:
        return self._active

    @override
    def background(self) -> str:
        return self._light[_BACKGROUND]

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
