"""docs/cli.md has a section for every management command the engine adds."""

import re

from django.core.management import get_commands

from tests.paths import REPO

PAGE = REPO / "docs" / "cli.md"
SECTION = re.compile(r"^## `([a-z_]+)`$", re.MULTILINE)
APP = "lapidarium.gates.cli.django"


def test_commands_page_has_a_section_per_engine_command():
    documented = set(SECTION.findall(PAGE.read_text(encoding="utf-8")))

    assert documented == {name for name, app in get_commands().items() if app == APP}
