"""Theme directories on disk: `theme.toml`, `tokens.css`, `theme.css`, templates."""

from __future__ import annotations

import re
import tomllib
from typing import TYPE_CHECKING, NoReturn, override

import tinycss2
from django.core.exceptions import ImproperlyConfigured

from lapidarium.pacts import ThemeDTO, ThemeStoreProtocol

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path

_DARK = re.compile(r"^@media.*prefers-color-scheme\s*:\s*dark")


def _fail(path: Path, *, line: int, message: str) -> NoReturn:
    msg = f"{path}, line {line}: {message}"
    raise ImproperlyConfigured(msg)


def _rules(css: str, path: Path) -> Iterator[tuple[str, str]]:
    """Each rule with a block in `css`: its prelude, and the CSS inside the block."""
    for rule in tinycss2.parse_rule_list(css, skip_comments=True, skip_whitespace=True):
        if rule.type == "error":
            _fail(path, line=rule.source_line, message=rule.message)
        if rule.content is None:
            continue
        prelude = tinycss2.serialize(rule.prelude).strip()
        if rule.type == "at-rule":
            prelude = f"@{rule.lower_at_keyword} {prelude}"
        yield prelude, tinycss2.serialize(rule.content)


def _root_tokens(css: str, path: Path) -> dict[str, str]:
    """Return the custom properties that `:root` rules directly in `css` set."""
    tokens: dict[str, str] = {}
    for prelude, body in _rules(css, path):
        if prelude != ":root":
            continue
        for item in tinycss2.parse_blocks_contents(
            body, skip_comments=True, skip_whitespace=True
        ):
            if item.type == "error":
                _fail(path, line=item.source_line, message=item.message)
            if item.type == "declaration" and item.name.startswith("--"):
                tokens[item.name] = tinycss2.serialize(item.value).strip()
    return tokens


def _optional(value: object) -> str | None:
    return None if value is None else str(value)


def read_theme(directory: Path) -> ThemeDTO:
    """`ImproperlyConfigured` when `tokens.css` does not parse."""
    manifest = directory / "theme.toml"
    meta = tomllib.loads(manifest.read_text()) if manifest.is_file() else {}
    path = directory / "tokens.css"
    css = path.read_text()
    templates = directory / "templates"
    return ThemeDTO(
        key=directory.name,
        name=str(meta.get("name", directory.name)),
        version=_optional(meta.get("version")),
        engine=_optional(meta.get("engine")),
        fonts=tuple(str(url) for url in meta.get("fonts", [])),
        has_stylesheet=(directory / "theme.css").is_file(),
        tokens=_root_tokens(css, path),
        dark_tokens={
            name: value
            for prelude, body in _rules(css, path)
            if _DARK.search(prelude)
            for name, value in _root_tokens(body, path).items()
        },
        templates=tuple(
            sorted(
                path.relative_to(templates).as_posix()
                for path in templates.rglob("*")
                if path.is_file()
            )
        ),
    )


class ThemeFiles(ThemeStoreProtocol):
    """Read once per process: themes ship with the code and change with a deploy."""

    def __init__(self, *, layers: Sequence[Path], engine_templates: Path) -> None:
        self._layers = tuple(read_theme(directory) for directory in layers)
        self._engine_templates = frozenset(
            path.relative_to(engine_templates).as_posix()
            for path in engine_templates.rglob("*")
            if path.is_file()
        )

    @override
    def layers(self) -> tuple[ThemeDTO, ...]:
        return self._layers

    @override
    def engine_templates(self) -> frozenset[str]:
        return self._engine_templates
