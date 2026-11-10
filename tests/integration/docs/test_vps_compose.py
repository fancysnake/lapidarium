"""The VPS example env lists every variable the compose file leaves open.

Settings come from the configuration page; variables only the compose file
reads come from the table on the deployment page.
"""

import re

import yaml

from lapidarium.edges import settings
from tests.env_docs import EXTERNAL, default
from tests.paths import REPO

COMPOSE = REPO / "docker" / "compose"
EXAMPLE = COMPOSE / "vps.env.example"
VPS = COMPOSE / "vps.yaml"
DEPLOYMENT = REPO / "docs" / "deployment.md"
ROW = re.compile(r"^\| `([A-Z_]+)` \|", re.MULTILINE)
KEY = re.compile(r"^(?:# )?([A-Z_]+)=", re.MULTILINE)
SHOWN = re.compile(r"^# ([A-Z_]+)=(.*)$", re.MULTILINE)
REFERENCE = re.compile(r"\$\{([A-Z_]+)")
OPTIONAL = "# --- Optional; the values shown are the defaults ---"


def _compose_variables() -> set[str]:
    _, section = DEPLOYMENT.read_text(encoding="utf-8").split("\n## Compose\n")
    return set(ROW.findall(section.split("\n## ", 1)[0]))


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
        _compose_variables()
    )


def test_example_shows_the_defaults_of_the_settings():
    _, optional = EXAMPLE.read_text(encoding="utf-8").split(OPTIONAL)
    shown = dict(SHOWN.findall(optional))
    # The compose file sets its own default for what it wires.
    scheme = {
        name: spec
        for name, spec in settings.env.scheme.items()
        if name in shown.keys() - _wired()
    }

    assert {
        name: default(shown[name] or "empty", cast)
        for name, (cast, _) in scheme.items()
    } == {name: default for name, (_, default) in scheme.items()}
