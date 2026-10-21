"""The theme contract: required tokens, contrast pairs, and what a theme holds."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class ProblemLevel(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class ThemeProblem(StrEnum):
    """A breach of the theme contract; the code's first letter gives its level."""

    MISSING_REQUIRED = "E001"
    LOW_CONTRAST = "E002"
    NO_ENGINE = "W001"
    OTHER_ENGINE = "W002"
    STALE_OVERRIDE = "W003"

    @property
    def level(self) -> ProblemLevel:
        return ProblemLevel.ERROR if self.startswith("E") else ProblemLevel.WARNING


# Every token a page may rely on. Renaming one breaks themes.
REQUIRED_TOKENS = frozenset(
    {
        "--color-bg",
        "--color-surface",
        "--color-surface-2",
        "--color-surface-band",
        "--color-text",
        "--color-text-strong",
        "--color-text-muted",
        "--color-border",
        "--color-border-soft",
        "--color-link",
        "--color-link-hover",
        "--color-brand",
        "--color-brand-contrast",
        "--color-type-default",
        "--color-type-default-tint",
        "--font-body",
        "--font-display",
        "--font-label",
        "--text-base",
        "--text-label",
        "--text-h1",
        "--text-h1-detail",
        "--text-h2",
        *(f"--space-{step}" for step in range(1, 10)),
        "--max-width",
        "--gutter",
        "--radius",
        "--radius-lg",
        "--line-strong",
    }
)
# Text colour on background colour: each pair must read, so each token is #rrggbb.
CONTRAST_PAIRS = (
    ("--color-text", "--color-bg"),
    ("--color-brand", "--color-bg"),
    ("--color-brand-contrast", "--color-brand"),
    ("--color-type-default", "--color-bg"),
    ("--color-type-default", "--color-type-default-tint"),
)
PAIRED_TOKENS = frozenset(token for pair in CONTRAST_PAIRS for token in pair)
HEX_COLOUR = r"#[0-9a-fA-F]{6}"


class ThemeDTO(BaseModel):
    """A theme directory as read: `theme.toml` and the tokens its CSS sets."""

    model_config = ConfigDict(frozen=True)

    key: str
    name: str
    version: str | None
    engine: str | None
    fonts: tuple[str, ...]
    has_stylesheet: bool
    tokens: dict[str, str]
    dark_tokens: dict[str, str]
    templates: tuple[str, ...]


class StylesheetDTO(BaseModel):
    """A stylesheet a page links: a static file path, or an external URL."""

    model_config = ConfigDict(frozen=True)

    href: str
    external: bool


class SiteThemeDTO(BaseModel):
    """The active theme as pages see it: stylesheets in load order."""

    model_config = ConfigDict(frozen=True)

    key: str
    name: str
    version: str | None
    stylesheets: tuple[StylesheetDTO, ...]


class ProblemDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: ThemeProblem
    message: str


class ThemeStoreProtocol(Protocol):
    def layers(self) -> tuple[ThemeDTO, ...]:
        """Return the layers in load order: the base first, the active theme last."""

    def engine_templates(self) -> frozenset[str]:
        """Paths of the templates the engine ships, as themes override them."""
