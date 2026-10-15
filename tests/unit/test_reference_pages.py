"""The manual's reference pages against the code they describe."""

import re
from argparse import ArgumentParser
from pathlib import Path

from django.core.management import get_commands, load_command_class

from lapidarium.edges import settings

DOCS = Path(__file__).resolve().parents[2] / "docs"
# Read straight from the environment by Django or a library, not by env().
_OUTSIDE_SCHEME = {"DATABASE_URL": ""}


def _first_block(page, language):
    text = (DOCS / page).read_text()
    match = re.search(rf"```{language}\n(.*?)```", text, re.DOTALL)
    assert match, f"{page} has no {language} block"
    return match.group(1).splitlines()


def _as_written(default):
    if isinstance(default, bool):
        return str(default).lower()
    if isinstance(default, list):
        return ",".join(default)
    return str(default)


def test_configuration_page_lists_every_variable_with_its_default():
    documented = dict(
        line.split("=", 1) for line in _first_block("configuration.md", "dotenv")
    )
    declared = {
        name: _as_written(spec[1]) if isinstance(spec, tuple) else ""
        for name, spec in settings.env.scheme.items()
    } | _OUTSIDE_SCHEME

    assert documented == declared


def test_cli_page_shows_every_command_usage():
    documented = _first_block("cli.md", "text")
    usages = []
    for name, app in sorted(get_commands().items()):
        if app.startswith("lapidarium."):
            parser = ArgumentParser(prog=name, add_help=False)
            load_command_class(app, name).add_arguments(parser)
            usages.append(" ".join(parser.format_usage().split()[1:]))

    assert documented == usages
