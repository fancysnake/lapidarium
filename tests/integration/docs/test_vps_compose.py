"""The VPS example env lists every variable the compose file leaves open.

Settings come from the configuration page; variables only the compose file
reads come from the table on the deployment page.
"""

import re

import yaml

from lapidarium.edges import settings
from tests.env_docs import EXTERNAL, mismatched_defaults, table_rows
from tests.paths import REPO

COMPOSE = REPO / "docker" / "compose"
EXAMPLE = COMPOSE / "vps.env.example"
VPS = COMPOSE / "vps.yaml"
KEY = re.compile(r"^(?:# )?([A-Z_]+)=", re.MULTILINE)
SHOWN = re.compile(r"^# ([A-Z_]+)=(.*)$", re.MULTILINE)
REFERENCE = re.compile(r"\$\{([A-Z_]+)")
OPTIONAL = "# --- Optional; the values shown are the defaults ---"


def _wired() -> set[str]:
    return set(
        yaml.safe_load(VPS.read_text(encoding="utf-8"))["services"]["web"][
            "environment"
        ]
    )


def test_example_lists_every_variable_the_compose_file_leaves_open():
    listed = set(KEY.findall(EXAMPLE.read_text(encoding="utf-8")))
    referenced = set(REFERENCE.findall(VPS.read_text(encoding="utf-8")))

    assert referenced <= listed
    assert listed | _wired() == settings.env.scheme.keys() | EXTERNAL | (
        table_rows("Compose")
    )


def test_example_shows_the_defaults_of_the_settings():
    _, optional = EXAMPLE.read_text(encoding="utf-8").split(OPTIONAL)
    # The compose file sets its own default for what it wires.
    unwired = {
        name: value for name, value in SHOWN.findall(optional) if name not in _wired()
    }

    assert not mismatched_defaults(unwired)
