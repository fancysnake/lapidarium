"""Every variable the settings read is documented, declared and deployed.

docs/configuration.md documents it, env/schema.env declares it, and the deploy
workflow exports it to varlock.
"""

import re

import yaml

from lapidarium.edges import settings
from tests.env_docs import EXTERNAL, REQUIRED, default
from tests.paths import REPO

PAGE = REPO / "docs" / "configuration.md"
SCHEMA = REPO / "env" / "schema.env"
WORKFLOW = REPO / ".github" / "workflows" / "deploy-coolify.yml"
PAYLOAD_STEP = "Build Coolify env payload and validate with varlock"
ROW = re.compile(r"^\| `([A-Z_]+)` \| ([^|]+?) \|", re.MULTILINE)
KEY = re.compile(r"^([A-Z_]+)=", re.MULTILINE)


def _variables() -> set[str]:
    return settings.env.scheme.keys() | EXTERNAL


def test_configuration_page_lists_every_variable_with_its_default():
    rows = dict(ROW.findall(PAGE.read_text(encoding="utf-8")))
    raw: dict[str, type | tuple[type, object]] = settings.env.scheme
    scheme = {
        name: spec if isinstance(spec, tuple) else (spec, REQUIRED)
        for name, spec in raw.items()
    }

    assert set(rows) == _variables()
    assert {name: default(rows[name], cast) for name, (cast, _) in scheme.items()} == {
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
