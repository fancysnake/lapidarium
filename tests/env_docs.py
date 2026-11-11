"""What the tests of the configuration and deployment docs share."""

import re
from typing import TYPE_CHECKING

import environ

from lapidarium.edges import settings
from tests.paths import REPO

if TYPE_CHECKING:
    from collections.abc import Mapping

REQUIRED = "required"
# Read by a library, or with a default the scheme cannot express.
EXTERNAL = {"GOOGLE_APPLICATION_CREDENTIALS", "TRUSTED_PROXY_HOPS"}
DEPLOYMENT = REPO / "docs" / "deployment.md"
ROW = re.compile(r"^\| `([A-Z_]+)` \|", re.MULTILINE)


def default(cell: str, cast: type) -> object:
    """Parse a documented default the way the settings would read it."""
    if cell == REQUIRED:
        return REQUIRED
    return environ.Env.parse_value("" if cell == "empty" else cell.strip("`"), cast)


def mismatched_defaults(shown: Mapping[str, str]) -> dict[str, tuple[object, object]]:
    """Map each setting whose shown default differs to both defaults.

    An empty value in `shown` stands for an empty default.
    """
    scheme = {name: spec for name, spec in settings.env.scheme.items() if name in shown}
    return {
        name: (parsed, expected)
        for name, (cast, expected) in scheme.items()
        if (parsed := default(shown[name] or "empty", cast)) != expected
    }


def table_rows(heading: str) -> set[str]:
    """Return the variables in the tables of one deployment page section."""
    _, section = DEPLOYMENT.read_text(encoding="utf-8").split(f"\n## {heading}\n")
    return set(ROW.findall(section.split("\n## ", 1)[0]))
