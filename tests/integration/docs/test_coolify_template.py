"""The Coolify template agrees with the settings, the VPS setup and its docs.

Coolify gets one file, so the template repeats what the VPS setup keeps in
three; the deployment page lists what the template asks the operator for.
"""

import re

import yaml

from lapidarium.edges import settings
from tests.env_docs import EXTERNAL, mismatched_defaults, table_rows
from tests.paths import REPO

COMPOSE = REPO / "docker" / "compose"
TEMPLATE = (COMPOSE / "coolify.yaml").read_text(encoding="utf-8")
SERVICES = yaml.safe_load(TEMPLATE)["services"]
WEB: dict[str, str] = SERVICES["web"]["environment"]
VPS_WEB: dict[str, str] = yaml.safe_load(
    (COMPOSE / "vps.yaml").read_text(encoding="utf-8")
)["services"]["web"]["environment"]
# The operator may set `${NAME:-default}` and must set `${NAME:?}`; Coolify
# fills a bare `${NAME}`. `$${NAME}` is left for the container's shell.
ASKED = re.compile(r"(?<!\$)\$\{([A-Z_]+):(?:-([^}]*)|\?[^}]*)\}")


def _asked() -> dict[str, str | None]:
    """Map each variable the template asks for to its default; None if required."""
    return {match[1]: match[2] for match in ASKED.finditer(TEMPLATE)}


def test_template_passes_settings_with_their_defaults():
    defaults = {name: value for name, value in _asked().items() if value is not None}

    assert WEB.keys() <= settings.env.scheme.keys() | EXTERNAL
    assert not mismatched_defaults(defaults)


def test_template_wires_the_container_like_the_vps_setup():
    wired = {name: value for name, value in VPS_WEB.items() if "${" not in value}

    assert {name: WEB.get(name) for name in wired} == wired


def test_template_carries_the_caddyfile_of_the_vps_setup():
    caddyfile = (COMPOSE / "Caddyfile").read_text(encoding="utf-8")
    mount = next(
        volume for volume in SERVICES["caddy"]["volumes"] if isinstance(volume, dict)
    )

    # The file's opening comment describes the VPS certificate.
    assert mount["content"] == "".join(
        line for line in caddyfile.splitlines(keepends=True) if not line.startswith("#")
    )


def test_deployment_page_lists_what_the_template_asks_for():
    assert table_rows("Coolify") == set(_asked())
