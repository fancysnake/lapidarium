"""The Coolify template agrees with the settings, the VPS setup and its docs.

Coolify gets one file, so the template repeats what the VPS setup keeps in
three; the deployment page lists what the template asks the operator for.
"""

import re

import yaml

from lapidarium.edges import settings
from tests.env_docs import EXTERNAL, default
from tests.paths import REPO

COMPOSE = REPO / "docker" / "compose"
SERVICES = yaml.safe_load((COMPOSE / "coolify.yaml").read_text(encoding="utf-8"))[
    "services"
]
WEB: dict[str, str] = SERVICES["web"]["environment"]
VPS_WEB = yaml.safe_load((COMPOSE / "vps.yaml").read_text(encoding="utf-8"))[
    "services"
]["web"]["environment"]
DEPLOYMENT = REPO / "docs" / "deployment.md"
ROW = re.compile(r"^\| `([A-Z_]+)` \|", re.MULTILINE)
# A variable the operator may set: `${NAME:-default}` or `${NAME:?}`.
ASKED = re.compile(r"^\$\{([A-Z_]+):(?:-(.*)|\?)\}$")
GENERATED = "SERVICE_"


def _asked() -> dict[str, str | None]:
    matches = (ASKED.match(value) for value in WEB.values())
    return {match[1]: match[2] for match in matches if match}


def test_template_passes_settings_with_their_defaults():
    scheme = {
        name: spec
        for name, spec in settings.env.scheme.items()
        if _asked().get(name) is not None
    }

    assert WEB.keys() <= settings.env.scheme.keys() | EXTERNAL
    assert {
        name: default(_asked()[name] or "empty", cast)
        for name, (cast, _) in scheme.items()
    } == {name: default for name, (_, default) in scheme.items()}


def test_template_wires_the_container_like_the_vps_setup():
    fixed = ("ENV", "DEBUG", "MEDIA_ROOT", "MEDIA_URL")

    assert {name: WEB[name] for name in fixed} == {
        name: VPS_WEB[name] for name in fixed
    }


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
    _, section = DEPLOYMENT.read_text(encoding="utf-8").split("\n## Coolify\n")
    referenced = set(
        re.findall(
            # `$${NAME}` is left for the container's shell.
            r"(?<!\$)\$\{([A-Z_]+)",
            (COMPOSE / "coolify.yaml").read_text(encoding="utf-8"),
        )
    )

    assert set(ROW.findall(section.split("\n## ", 1)[0])) == {
        name for name in referenced if not name.startswith(GENERATED)
    }
