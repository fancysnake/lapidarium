"""Every docs page carries a search-snippet description of at most 160 characters.

The homepage has none of its own: it falls back to the site description.
"""

import re
import tomllib

import pytest
import yaml

from tests.paths import REPO

DOCS = REPO / "docs"
CONFIG = yaml.safe_load((REPO / "mkdocs.yml").read_text(encoding="utf-8"))
FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
HOMEPAGE = "index.md"
LIMIT = 160


def _pages(nav: list[str | dict[str, object]]) -> list[str]:
    pages = []
    for item in nav:
        if isinstance(item, str):
            pages.append(item)
        else:
            for child in item.values():
                pages.extend(_pages(child) if isinstance(child, list) else [child])
    return pages


def _description(page: str) -> str:
    text = (DOCS / page).read_text(encoding="utf-8")
    if (match := FRONT_MATTER.match(text)) is None:
        return ""
    return (yaml.safe_load(match.group(1)) or {}).get("description", "")


@pytest.mark.parametrize(
    "page", [page for page in _pages(CONFIG["nav"]) if page != HOMEPAGE]
)
def test_page_has_a_short_description(page):
    assert 0 < len(_description(page)) <= LIMIT


def test_homepage_falls_back_to_a_short_site_description():
    assert not _description(HOMEPAGE)
    assert 0 < len(CONFIG["site_description"]) <= LIMIT


def test_site_description_matches_the_package_description():
    with (REPO / "pyproject.toml").open("rb") as file:
        project = tomllib.load(file)["project"]
    assert CONFIG["site_description"] == project["description"]
