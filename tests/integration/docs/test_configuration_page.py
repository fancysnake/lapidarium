"""Every variable the settings read is documented, declared and deployed.

docs/configuration.md documents it, env/schema.env declares it, and the deploy
workflow exports it to varlock.
"""

import re

import environ
import yaml

from lapidarium.edges import settings
from tests.paths import REPO

PAGE = REPO / "docs" / "configuration.md"
SCHEMA = REPO / "env" / "schema.env"
WORKFLOW = REPO / ".github" / "workflows" / "deploy-coolify.yml"
PAYLOAD_STEP = "Build Coolify env payload and validate with varlock"
ROW = re.compile(r"^\| `([A-Z_]+)` \| ([^|]+?) \|", re.MULTILINE)
KEY = re.compile(r"^([A-Z_]+)=", re.MULTILINE)
REQUIRED = "required"
# Read by a library, or with a default the scheme cannot express.
EXTERNAL = {"GOOGLE_APPLICATION_CREDENTIALS", "TRUSTED_PROXY_HOPS"}


def _variables() -> set[str]:
    return settings.env.scheme.keys() | EXTERNAL


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

    assert set(rows) == _variables()
    assert {name: _default(rows[name], cast) for name, (cast, _) in scheme.items()} == {
        name: default for name, (_, default) in scheme.items()
    }


def test_schema_declares_every_variable():
    declared = set(KEY.findall(SCHEMA.read_text(encoding="utf-8")))

    assert declared == _variables() | {"DJANGO_SETTINGS_MODULE"}


def test_deploy_workflow_exports_every_variable():
    steps = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["deploy"][
        "steps"
    ]
    payload = next(step for step in steps if step.get("name") == PAYLOAD_STEP)

    assert payload["env"].keys() == _variables()
