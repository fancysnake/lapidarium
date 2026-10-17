"""The active theme against its contract: tokens, engine, overrides, contrast."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from lapidarium.mills.colour import contrast_ratio
from lapidarium.pacts import (
    REQUIRED_TOKENS,
    ProblemDTO,
    ProblemLevel,
    SiteThemeDTO,
    StylesheetDTO,
    ThemeServiceProtocol,
)
from lapidarium.specs import CONTRAST_FLOOR

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from lapidarium.pacts import ThemeStoreProtocol

_HEX = re.compile(r"#[0-9a-fA-F]{6}")
_FALLBACK_BACKGROUND = "#ffffff"
_ENGINE_STYLESHEET = "lapidarium/css/base.css"
# Text colour on background colour: each pair must read.
_PAIRS = (
    ("--color-text", "--color-bg"),
    ("--color-brand", "--color-bg"),
    ("--color-brand-contrast", "--color-brand"),
    ("--color-type-default", "--color-bg"),
    ("--color-type-default", "--color-type-default-tint"),
)
_PAIRED = sorted({token for pair in _PAIRS for token in pair})


def _release(version: str) -> tuple[str, ...]:
    """Return the part of a version that must match: major, or 0.minor before 1.0."""
    parts = version.split(".")
    return tuple(parts[:2]) if parts[0] == "0" else tuple(parts[:1])


def _contrast_problems(
    tokens: Mapping[str, str], *, scheme: str
) -> Iterator[ProblemDTO]:
    for token in _PAIRED:
        if token in tokens and not _HEX.fullmatch(tokens[token]):
            yield ProblemDTO(
                level=ProblemLevel.ERROR,
                code="E003",
                message=(
                    f"{token} ({scheme}) is {tokens[token]!r}; the contrast check"
                    " needs #rrggbb."
                ),
            )
    for text, background in _PAIRS:
        first, second = tokens.get(text, ""), tokens.get(background, "")
        if not (_HEX.fullmatch(first) and _HEX.fullmatch(second)):
            continue
        if (ratio := contrast_ratio(first, second)) < CONTRAST_FLOOR:
            yield ProblemDTO(
                level=ProblemLevel.ERROR,
                code="E002",
                message=(
                    f"{text} on {background} ({scheme}) has contrast"
                    f" {ratio:.2f}:1, needs {CONTRAST_FLOOR}:1."
                ),
            )


class ThemeService(ThemeServiceProtocol):
    """Read through `store`; checked against `engine_version`."""

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
        self._has_dark = any(layer.dark_tokens for layer in self._layers)

    @override
    def active(self) -> SiteThemeDTO:
        fonts = [url for layer in self._layers for url in layer.fonts]
        paths = [
            *(f"themes/{layer.key}/tokens.css" for layer in self._layers),
            _ENGINE_STYLESHEET,
            *(
                f"themes/{layer.key}/theme.css"
                for layer in self._layers
                if layer.has_stylesheet
            ),
        ]
        active = self._layers[-1]
        return SiteThemeDTO(
            key=active.key,
            name=active.name,
            version=active.version,
            stylesheets=(
                *(StylesheetDTO(href=url, external=True) for url in fonts),
                *(StylesheetDTO(href=path, external=False) for path in paths),
            ),
        )

    @override
    def background(self) -> str:
        """White unless `--color-bg` is `#rrggbb`; `check` reports it when not."""
        background = self._light.get("--color-bg", "")
        return background if _HEX.fullmatch(background) else _FALLBACK_BACKGROUND

    @override
    def dark_background(self) -> str | None:
        """None without a dark scheme, or unless its `--color-bg` is `#rrggbb`."""
        background = self._dark.get("--color-bg", "")
        return background if self._has_dark and _HEX.fullmatch(background) else None

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
                level=ProblemLevel.ERROR,
                code="E001",
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
                level=ProblemLevel.WARNING,
                code="W001",
                message=f"Theme {active.key!r} declares no engine version.",
            )
        elif _release(active.engine) != _release(self._engine_version):
            yield ProblemDTO(
                level=ProblemLevel.WARNING,
                code="W002",
                message=(
                    f"Theme {active.key!r} is built for engine {active.engine};"
                    f" this is {self._engine_version}."
                ),
            )

    def _stale_overrides(self) -> Iterator[ProblemDTO]:
        engine_templates = self._store.engine_templates()
        for path in sorted(set(self._layers[-1].templates) - engine_templates):
            yield ProblemDTO(
                level=ProblemLevel.WARNING,
                code="W003",
                message=f"Theme overrides {path}, which the engine no longer has.",
            )
