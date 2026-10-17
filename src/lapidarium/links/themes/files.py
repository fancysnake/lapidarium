"""Theme directories on disk: `theme.toml`, `tokens.css`, `theme.css`, templates."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING, NoReturn, Protocol, override

import tinycss2
from django.core.exceptions import ImproperlyConfigured

from lapidarium.pacts import ThemeDTO, ThemeStoreProtocol

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence
    from pathlib import Path

_ROOT = ":root"
_DARK = "(prefers-color-scheme:dark)"


def _fail(path: Path, *, line: int, message: str) -> NoReturn:
    msg = f"{path}, line {line}: {message}"
    raise ImproperlyConfigured(msg)


class _Rule(Protocol):
    """A tinycss2 rule with a block, as read here; tinycss2 ships no types."""

    type: str
    # Set on at-rules only.
    lower_at_keyword: str
    prelude: list[object]
    content: list[object]


def _prelude(rule: _Rule) -> str:
    """Return the prelude of `rule` lowercased, without whitespace."""
    return "".join(str(tinycss2.serialize(rule.prelude)).split()).lower()


def _rules(css: str | list[object], path: Path) -> list[_Rule]:
    """Each rule with a block in `css`: a file's text, or the tokens of a block."""
    rules: list[_Rule] = []
    for rule in tinycss2.parse_rule_list(css, skip_comments=True, skip_whitespace=True):
        if rule.type == "error":
            _fail(path, line=rule.source_line, message=rule.message)
        if rule.content is not None:
            rules.append(rule)
    return rules


def _dark_blocks(rules: Iterable[_Rule]) -> Iterator[list[object]]:
    """Yield the tokens inside each dark-scheme `@media` among `rules`."""
    for rule in rules:
        if (
            rule.type == "at-rule"
            and rule.lower_at_keyword == "media"
            and _DARK in _prelude(rule)
        ):
            yield rule.content


def _root_tokens(rules: Iterable[_Rule], path: Path) -> dict[str, str]:
    """Return the custom properties that the `:root` rules among `rules` set."""
    tokens: dict[str, str] = {}
    for rule in rules:
        if rule.type != "qualified-rule" or _prelude(rule) != _ROOT:
            continue
        for item in tinycss2.parse_blocks_contents(
            rule.content, skip_comments=True, skip_whitespace=True
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
    rules = _rules(path.read_text(), path)
    templates = directory / "templates"
    return ThemeDTO(
        key=directory.name,
        name=str(meta.get("name", directory.name)),
        version=_optional(meta.get("version")),
        engine=_optional(meta.get("engine")),
        fonts=tuple(str(url) for url in meta.get("fonts", [])),
        has_stylesheet=(directory / "theme.css").is_file(),
        tokens=_root_tokens(rules, path),
        dark_tokens={
            name: value
            for block in _dark_blocks(rules)
            for name, value in _root_tokens(_rules(block, path), path).items()
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
