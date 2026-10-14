"""Theme directories on disk: `theme.toml`, `tokens.css`, `theme.css`, templates."""

from __future__ import annotations

import re
import tomllib
from typing import TYPE_CHECKING, override

from lapidarium.pacts import ThemeDTO, ThemeStoreProtocol

if TYPE_CHECKING:
    from pathlib import Path

_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_DECLARATION = re.compile(r"(--[\w-]+)\s*:\s*([^;{}]+)")
_DARK = re.compile(r"prefers-color-scheme\s*:\s*dark")


def _media_blocks(css: str) -> tuple[str, list[tuple[str, str]]]:
    """Split `css` into what lies outside `@media` and each query with its body."""
    outside: list[str] = []
    blocks: list[tuple[str, str]] = []
    position = 0
    while (start := css.find("@media", position)) != -1:
        outside.append(css[position:start])
        opening = css.index("{", start)
        depth, index = 1, opening + 1
        while depth:
            depth += {"{": 1, "}": -1}.get(css[index], 0)
            index += 1
        blocks.append((css[start:opening], css[opening + 1 : index - 1]))
        position = index
    outside.append(css[position:])
    return "".join(outside), blocks


def _tokens(css: str) -> dict[str, str]:
    return {name: value.strip() for name, value in _DECLARATION.findall(css)}


def read_theme(directory: Path) -> ThemeDTO:
    manifest = directory / "theme.toml"
    meta = tomllib.loads(manifest.read_text()) if manifest.is_file() else {}
    css = _COMMENT.sub("", (directory / "tokens.css").read_text())
    light, blocks = _media_blocks(css)
    templates = directory / "templates"
    return ThemeDTO(
        key=directory.name,
        name=str(meta.get("name", directory.name)),
        version=str(meta.get("version", "")),
        engine=str(meta.get("engine", "")),
        fonts=tuple(str(url) for url in meta.get("fonts", [])),
        has_stylesheet=(directory / "theme.css").is_file(),
        tokens=_tokens(light),
        dark_tokens={
            name: value
            for query, body in blocks
            if _DARK.search(query)
            for name, value in _tokens(body).items()
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

    def __init__(self, *, base: Path, active: Path, engine_templates: Path) -> None:
        self._base = read_theme(base)
        self._active = self._base if active == base else read_theme(active)
        self._engine_templates = frozenset(
            path.relative_to(engine_templates).as_posix()
            for path in engine_templates.rglob("*")
            if path.is_file()
        )

    @override
    def base(self) -> ThemeDTO:
        return self._base

    @override
    def active(self) -> ThemeDTO:
        return self._active

    @override
    def engine_templates(self) -> frozenset[str]:
        return self._engine_templates
