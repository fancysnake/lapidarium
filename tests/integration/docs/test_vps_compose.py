"""The VPS example env lists every variable the compose file leaves open.

Settings come from the configuration page; variables only the compose file
reads come from the table on the deployment page.
"""

import re

import yaml

from lapidarium.edges import settings
from tests.paths import REPO

from .test_configuration_page import EXTERNAL

COMPOSE = REPO / "docker" / "compose"
EXAMPLE = COMPOSE / "vps.env.example"
VPS = COMPOSE / "vps.yaml"
DEPLOYMENT = REPO / "docs" / "deployment.md"
ROW = re.compile(r"^\| `([A-Z_]+)` \|", re.MULTILINE)
KEY = re.compile(r"^(?:# )?([A-Z_]+)=", re.MULTILINE)


def _compose_variables() -> set[str]:
    return set(ROW.findall(DEPLOYMENT.read_text(encoding="utf-8")))


def test_example_lists_every_variable_the_compose_file_leaves_open():
    listed = set(KEY.findall(EXAMPLE.read_text(encoding="utf-8")))
    wired = yaml.safe_load(VPS.read_text(encoding="utf-8"))["services"]["web"][
        "environment"
    ].keys()

    assert listed | wired == settings.env.scheme.keys() | EXTERNAL | (
        _compose_variables()
    )
