"""The active theme against its contract: tokens, engine, overrides, contrast."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from lapidarium.mills.schema import contrast_ratio
from lapidarium.pacts import (
    REQUIRED_TOKENS,
    ProblemDTO,
    ProblemLevel,
    ThemeServiceProtocol,
)
from lapidarium.specs import CONTRAST_FLOOR

if TYPE_CHECKING:
    from collections.abc import Mapping

    from lapidarium.pacts import ThemeDTO, ThemeStoreProtocol

_HEX = re.compile(r"#[0-9a-fA-F]{6}")
_FALLBACK_BACKGROUND = "#ffffff"
# Text colour on background colour: each pair must read.
_PAIRS = (
    ("--color-text", "--color-bg"),
    ("--color-brand", "--color-bg"),
    ("--color-brand-contrast", "--color-brand"),
    ("--color-type-default", "--color-bg"),
    ("--color-type-default", "--color-type-default-tint"),
)


def _release(version: str) -> tuple[str, ...]:
    """Return the part of a version that must match: major, or 0.minor before 1.0."""
    parts = version.split(".")
    return tuple(parts[:2]) if parts[0] == "0" else tuple(parts[:1])


def _contrast_problems(tokens: Mapping[str, str], *, scheme: str) -> list[ProblemDTO]:
    problems: list[ProblemDTO] = []
    for text, background in _PAIRS:
        first, second = tokens.get(text, ""), tokens.get(background, "")
        if not (_HEX.fullmatch(first) and _HEX.fullmatch(second)):
            continue
        if (ratio := contrast_ratio(first, second)) < CONTRAST_FLOOR:
            problems.append(
                ProblemDTO(
                    level=ProblemLevel.ERROR,
                    code="E002",
                    message=(
                        f"{text} on {background} ({scheme}) has contrast"
                        f" {ratio:.2f}:1, needs {CONTRAST_FLOOR}:1."
                    ),
                )
            )
    return problems


class ThemeService(ThemeServiceProtocol):
    """Read through `store`; checked against `engine_version`."""

    def __init__(self, *, store: ThemeStoreProtocol, engine_version: str) -> None:
        self._store = store
        self._engine_version = engine_version

    def tokens(self, *, dark: bool = False) -> dict[str, str]:
        """Return what the page sees: base tokens, then the active theme's."""
        base, active = self._store.base(), self._store.active()
        merged = {**base.tokens, **active.tokens}
        if dark:
            merged |= {**base.dark_tokens, **active.dark_tokens}
        return merged

    @override
    def active(self) -> ThemeDTO:
        return self._store.active()

    @override
    def background(self) -> str:
        background = self.tokens().get("--color-bg", "")
        return background if _HEX.fullmatch(background) else _FALLBACK_BACKGROUND

    @override
    def dark_background(self) -> str | None:
        """Return the background of the dark scheme, if the theme has one."""
        active, base = self._store.active(), self._store.base()
        background = active.dark_tokens.get(
            "--color-bg", base.dark_tokens.get("--color-bg", "")
        )
        return background if _HEX.fullmatch(background) else None

    @override
    def check(self) -> list[ProblemDTO]:
        active = self._store.active()
        problems = [
            ProblemDTO(
                level=ProblemLevel.ERROR,
                code="E001",
                message=f"No theme defines the required token {token}.",
            )
            for token in sorted(REQUIRED_TOKENS - self.tokens().keys())
        ]
        problems.extend(_contrast_problems(self.tokens(), scheme="light"))
        if self.dark_background():
            problems.extend(_contrast_problems(self.tokens(dark=True), scheme="dark"))
        if not active.engine:
            problems.append(
                ProblemDTO(
                    level=ProblemLevel.WARNING,
                    code="W001",
                    message=f"Theme {active.key!r} declares no engine version.",
                )
            )
        elif _release(active.engine) != _release(self._engine_version):
            problems.append(
                ProblemDTO(
                    level=ProblemLevel.WARNING,
                    code="W002",
                    message=(
                        f"Theme {active.key!r} is built for engine {active.engine};"
                        f" this is {self._engine_version}."
                    ),
                )
            )
        problems.extend(
            ProblemDTO(
                level=ProblemLevel.WARNING,
                code="W003",
                message=f"Theme overrides {path}, which the engine no longer has.",
            )
            for path in sorted(set(active.templates) - self._store.engine_templates())
        )
        return problems
