"""The container's first start step, run as the image runs it."""

import os
import subprocess
import sys

import pytest

COMMAND = [sys.executable, "-m", "lapidarium.edges.preflight"]


def _preflight(**changes):
    env = {k: v for k, v in os.environ.items() if k not in changes}
    env |= {k: v for k, v in changes.items() if v is not None}
    return subprocess.run(COMMAND, env=env, capture_output=True, text=True, check=False)


def test_a_complete_environment_passes_silently():
    result = _preflight()

    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


@pytest.mark.parametrize("value", (None, ""), ids=("missing", "empty"))
@pytest.mark.parametrize("name", ("SECRET_KEY", "DATABASE_URL"))
def test_a_missing_required_variable_stops_in_one_line_naming_it(name, value):
    result = _preflight(**{name: value})

    assert result.returncode == 1
    assert not result.stdout
    assert len(result.stderr.splitlines()) == 1
    assert name in result.stderr
