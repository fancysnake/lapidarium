"""The deploy workflow's env sync, run as the runner runs it against a fake Coolify."""

import json
import os
import subprocess

from tests.deploy_workflow import PAYLOAD_STEP, SYNC_STEP, deploy_steps
from tests.paths import REPO

API = "https://coolify.test/api/v1/applications/app-1"
SECRET = "resolved-secret-key-value"
# What GitHub supplies at least: the smallest set varlock accepts.
REQUIRED_SETTINGS = {
    "SECRET_KEY": SECRET,
    "ALLOWED_HOSTS": "example.com",
    "DATABASE_URL": "postgres://user:pass@db:5432/lapidarium",
}

# Logs `<method> <url>`, keeps each request body, answers as Coolify does. A
# DELETE removes the variable; with `lose-reply` present, curl then fails as it
# does when the reply is lost and the retry meets a 404.
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
echo "$method $url" >> "$FAKE_DIR/calls.log"
case "$method $url" in
  "GET "*/envs) cat "$FAKE_DIR/stored.json" ;;
  "DELETE "*)
    jq --arg id "${url##*/}" 'map(select(.uuid != $id))' "$FAKE_DIR/stored.json" \
      > "$FAKE_DIR/kept.json"
    mv "$FAKE_DIR/kept.json" "$FAKE_DIR/stored.json"
    if [ -e "$FAKE_DIR/lose-reply" ]; then exit 22; fi ;;
  "POST "*) echo '{"deployments": [{"deployment_uuid": "d1"}]}' ;;
  "GET "*/deployments/d1) echo '{"status": "finished"}' ;;
esac
"""


def _deploy(tmp_path, stored, *, lose_delete_reply=False):
    steps = deploy_steps()
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "curl").write_text(FAKE_CURL, encoding="utf-8")
    (fake_bin / "sleep").write_text("#!/bin/sh\n", encoding="utf-8")
    for tool in fake_bin.iterdir():
        tool.chmod(0o755)
    (tmp_path / "stored.json").write_text(json.dumps(stored), encoding="utf-8")
    if lose_delete_reply:
        (tmp_path / "lose-reply").touch()
    env = os.environ | {
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "RUNNER_TEMP": str(tmp_path),
        "FAKE_DIR": str(tmp_path),
        "COOLIFY_URL": "https://coolify.test",
        "COOLIFY_TOKEN": "token",
        "APP_UUID": "app-1",
        "IMAGE_TAG": "sha-1",
        # GitHub exports a variable the Environment lacks as an empty string;
        # the values the workflow fixes itself stay as written.
        **{
            key: REQUIRED_SETTINGS.get(key, "") if value.startswith("${{") else value
            for key, value in steps[PAYLOAD_STEP]["env"].items()
        },
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

    calls, sent, output = _deploy(tmp_path, stored)

    assert [call for call in calls if call.startswith("DELETE")] == [
        f"DELETE {API}/envs/emptied"
    ]
    assert sent.keys() == {"data"}
    assert {item["key"] for item in sent["data"]} == {
        "ENV",
        "DEBUG",
        "SECRET_KEY",
        "ALLOWED_HOSTS",
        "DATABASE_URL",
        "DJANGO_SETTINGS_MODULE",
    }
    assert SECRET not in output


def test_a_deploy_with_nothing_stored_to_clear_deletes_nothing(tmp_path):
    calls, _, _ = _deploy(
        tmp_path, [{"uuid": "still-set", "key": "ALLOWED_HOSTS", "is_preview": False}]
    )

    assert not [call for call in calls if call.startswith("DELETE")]


def test_a_delete_whose_reply_was_lost_does_not_stop_the_deploy(tmp_path):
    calls, _, _ = _deploy(
        tmp_path,
        [{"uuid": "emptied", "key": "SITE_NAME", "is_preview": False}],
        lose_delete_reply=True,
    )

    assert f"DELETE {API}/envs/emptied" in calls
    assert "POST https://coolify.test/api/v1/deploy?uuid=app-1" in calls
