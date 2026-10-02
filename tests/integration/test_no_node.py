"""Zero Node is a project rule: no manifest, no modules, no bundler config."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHECKED_DIRS = ("src", "tests", "docs", "docker", ".github")
FORBIDDEN = ("package.json", "package-lock.json", "node_modules", "vite.config.*")


def test_repository_has_no_node_artifacts():
    found = [path for name in FORBIDDEN for path in REPO.glob(name)]
    for directory in CHECKED_DIRS:
        found.extend(
            path for name in FORBIDDEN for path in (REPO / directory).rglob(name)
        )

    assert found == []
