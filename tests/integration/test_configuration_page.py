"""docs/configuration.md documents every variable the settings read."""

import re
from pathlib import Path

import environ

from lapidarium.edges import settings

PAGE = Path(__file__).resolve().parents[2] / "docs" / "configuration.md"
ROW = re.compile(r"^\| `([A-Z_]+)` \| ([^|]+?) \|", re.MULTILINE)
REQUIRED = "required"
UNDOCUMENTED = "undocumented"


def _documented(cell: str | None, cast: type) -> object:
    match cell:
        case None:
            return UNDOCUMENTED
        case "required":
            return REQUIRED
        case "empty":
            return environ.Env.parse_value("", cast)
        case _:
            return environ.Env.parse_value(cell.strip("`"), cast)


def test_configuration_page_gives_every_setting_its_default():
    rows = dict(ROW.findall(PAGE.read_text(encoding="utf-8")))
    scheme: dict[str, type | tuple[type, object]] = settings.env.scheme

    documented = {
        name: _documented(rows.get(name), spec[0] if isinstance(spec, tuple) else spec)
        for name, spec in scheme.items()
    }

    assert documented == {
        name: spec[1] if isinstance(spec, tuple) else REQUIRED
        for name, spec in scheme.items()
    }
