"""What the tests of the Coolify deploy workflow share."""

from typing import Any

import yaml

from tests.paths import REPO

WORKFLOW = REPO / ".github" / "workflows" / "deploy-coolify.yml"
PAYLOAD_STEP = "Build Coolify env payload and validate with varlock"
SYNC_STEP = "Sync env, pin image tag, deploy on Coolify and wait"


def deploy_steps() -> dict[str | None, dict[str, Any]]:
    """Return the deploy job's steps by name."""
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    return {step.get("name"): step for step in jobs["deploy"]["steps"]}
