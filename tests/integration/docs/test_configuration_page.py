"""docs/configuration.md documents every variable the settings read."""

import re

import environ

from lapidarium.edges import settings
from tests.paths import REPO

PAGE = REPO / "docs" / "configuration.md"
ROW = re.compile(r"^\| `([A-Z_]+)` \| ([^|]+?) \|", re.MULTILINE)
REQUIRED = "required"
# Read by a library, or with a default the scheme cannot express.
EXTERNAL = {"GOOGLE_APPLICATION_CREDENTIALS", "TRUSTED_PROXY_HOPS"}


def _default(cell: str, cast: type) -> object:
    if cell == REQUIRED:
        return REQUIRED
    return environ.Env.parse_value("" if cell == "empty" else cell.strip("`"), cast)


def test_configuration_page_lists_every_variable_with_its_default():
    rows = dict(ROW.findall(PAGE.read_text(encoding="utf-8")))
    raw: dict[str, type | tuple[type, object]] = settings.env.scheme
    scheme = {
        name: spec if isinstance(spec, tuple) else (spec, REQUIRED)
        for name, spec in raw.items()
    }

    assert set(rows) == scheme.keys() | EXTERNAL
    assert {name: _default(rows[name], cast) for name, (cast, _) in scheme.items()} == {
        name: default for name, (_, default) in scheme.items()
    }
