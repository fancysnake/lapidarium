"""The deploy workflow's env sync, run as the runner runs it against a fake Coolify."""

import json
import os
import subprocess

import yaml

from tests.paths import REPO

WORKFLOW = REPO / ".github" / "workflows" / "deploy-coolify.yml"
PAYLOAD_STEP = "Build Coolify env payload and validate with varlock"
SYNC_STEP = "Sync env, pin image tag, deploy on Coolify and wait"
API = "https://coolify.test/api/v1/applications/app-1"
SECRET = "resolved-secret-key-value"

# Logs `<method> <url>`, keeps each request body, answers as Coolify does.
FAKE_CURL = """#!/usr/bin/env bash
method=GET
url="${!#}"
while [ $# -gt 1 ]; do
  case "$1" in
    -X) method="$2"; shift ;;
    --data) cat > "$FAKE_DIR/body-${url##*/}.json"; shift ;;
  esac
  shift
done
echo "$method $1" >> "$FAKE_DIR/calls.log"
case "$method $1" in
  "GET "*/envs) cat "$FAKE_DIR/stored.json" ;;
  "POST "*) echo '{"deployments": [{"deployment_uuid": "d1"}]}' ;;
  "GET "*/deployments/d1) echo '{"status": "finished"}' ;;
esac
"""


def _deploy(tmp_path, stored, **github_environment):
    steps = {
        step.get("name"): step
        for step in yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"][
            "deploy"
        ]["steps"]
    }
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "curl").write_text(FAKE_CURL, encoding="utf-8")
    (fake_bin / "sleep").write_text("#!/bin/sh\n", encoding="utf-8")
    for tool in fake_bin.iterdir():
        tool.chmod(0o755)
    (tmp_path / "stored.json").write_text(json.dumps(stored), encoding="utf-8")
    env = os.environ | {
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "RUNNER_TEMP": str(tmp_path),
        "FAKE_DIR": str(tmp_path),
        "COOLIFY_URL": "https://coolify.test",
        "COOLIFY_TOKEN": "token",
        "APP_UUID": "app-1",
        "IMAGE_TAG": "sha-1",
        # GitHub exports a variable the Environment lacks as an empty string.
        **dict.fromkeys(steps[PAYLOAD_STEP]["env"], ""),
        **github_environment,
    }
    output = ""
    for name in (PAYLOAD_STEP, SYNC_STEP):
        result = subprocess.run(
            ["bash", "-c", steps[name]["run"]],
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        output += result.stdout + result.stderr
    calls = (tmp_path / "calls.log").read_text(encoding="utf-8").splitlines()
    sent = json.loads((tmp_path / "body-bulk.json").read_text(encoding="utf-8"))
    return calls, sent, output


def test_a_variable_emptied_in_github_is_deleted_from_coolify(tmp_path):
    stored = [
        {"uuid": "emptied", "key": "SITE_NAME", "is_preview": False},
        {"uuid": "preview-copy", "key": "SITE_NAME", "is_preview": True},
        {"uuid": "still-set", "key": "ALLOWED_HOSTS", "is_preview": False},
        {"uuid": "outside-schema", "key": "OPERATOR_OWN", "is_preview": False},
    ]

    calls, sent, output = _deploy(
        tmp_path,
        stored,
        ENV="production",
        SECRET_KEY=SECRET,
        ALLOWED_HOSTS="example.com",
        DATABASE_URL="postgres://user:pass@db:5432/lapidarium",
    )

    assert [call for call in calls if call.startswith("DELETE")] == [
        f"DELETE {API}/envs/emptied"
    ]
    assert sent.keys() == {"data"}
    assert {item["key"] for item in sent["data"]} == {
        "ENV",
        "SECRET_KEY",
        "ALLOWED_HOSTS",
        "DATABASE_URL",
        "DJANGO_SETTINGS_MODULE",
    }
    assert SECRET not in output


def test_a_deploy_with_nothing_stored_to_clear_deletes_nothing(tmp_path):
    calls, _, _ = _deploy(
        tmp_path,
        [{"uuid": "still-set", "key": "ALLOWED_HOSTS", "is_preview": False}],
        ENV="production",
        SECRET_KEY=SECRET,
        ALLOWED_HOSTS="example.com",
        DATABASE_URL="postgres://user:pass@db:5432/lapidarium",
    )

    assert not [call for call in calls if call.startswith("DELETE")]
