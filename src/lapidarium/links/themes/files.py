"""Theme directories on disk: `theme.toml`, `tokens.css`, `theme.css`, templates."""

from __future__ import annotations

import re
import tomllib
from typing import TYPE_CHECKING, NoReturn, Protocol, override

import tinycss2
from django.core.exceptions import ImproperlyConfigured

from lapidarium.pacts import HEX_COLOUR, PAIRED_TOKENS, ThemeDTO, ThemeStoreProtocol

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence
    from pathlib import Path

_ROOT = ":root"
_DARK = "(prefers-color-scheme:dark)"
_HEX = re.compile(HEX_COLOUR)


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
            if item.type != "declaration" or not item.name.startswith("--"):
                continue
            value = tinycss2.serialize(item.value).strip()
            if item.name in PAIRED_TOKENS and not _HEX.fullmatch(value):
                _fail(
                    path,
                    line=item.source_line,
                    message=f"{item.name} is {value!r}; it must be #rrggbb.",
                )
            tokens[item.name] = value
    return tokens


def _optional(value: object) -> str | None:
    return None if value is None else str(value)


def _relative_files(root: Path) -> tuple[str, ...]:
    """Every file under `root`, as sorted POSIX paths relative to it."""
    return tuple(
        sorted(
            file.relative_to(root).as_posix()
            for file in root.rglob("*")
            if file.is_file()
        )
    )


def read_theme(directory: Path, *, href: str) -> ThemeDTO:
    """`ImproperlyConfigured` when `tokens.css` does not parse or breaks the contract.

    The contract: each colour the contrast check reads is `#rrggbb`.
    `href` is the static path the directory is served under.
    """
    manifest = directory / "theme.toml"
    meta = tomllib.loads(manifest.read_text()) if manifest.is_file() else {}
    path = directory / "tokens.css"
    rules = _rules(path.read_text(), path)
    return ThemeDTO(
        key=directory.name,
        name=str(meta.get("name", directory.name)),
        version=_optional(meta.get("version")),
        engine=_optional(meta.get("engine")),
        fonts=tuple(str(url) for url in meta.get("fonts", [])),
        tokens_href=f"{href}/tokens.css",
        stylesheet_href=(
            f"{href}/theme.css" if (directory / "theme.css").is_file() else None
        ),
        tokens=_root_tokens(rules, path),
        dark_tokens={
            name: value
            for block in _dark_blocks(rules)
            for name, value in _root_tokens(_rules(block, path), path).items()
        },
        templates=_relative_files(directory / "templates"),
    )


class ThemeFiles(ThemeStoreProtocol):
    """Read once per process: themes ship with the code and change with a deploy."""

    def __init__(
        self, *, layers: Sequence[tuple[str, Path]], engine_templates: Path
    ) -> None:
        """`layers` holds (static path, directory) pairs in load order."""
        self._layers = tuple(
            read_theme(directory, href=href) for href, directory in layers
        )
        self._engine_templates = frozenset(_relative_files(engine_templates))

    @override
    def layers(self) -> tuple[ThemeDTO, ...]:
        return self._layers

    @override
    def engine_templates(self) -> frozenset[str]:
        return self._engine_templates
