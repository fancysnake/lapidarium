"""Export format v1 survives database → files → database on both demo sets."""

import filecmp

import pytest

from lapidarium.inits import Services
from lapidarium.links.content_files.markdown import ContentFilesStore

DEMOS = ("dev", "ttrpg")

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("media_root"),
]
STAMPS = ("created_at", "updated_at")


def _by_key(bundle):
    entries = {
        (e["type"], e["slug"]): {
            **{k: v for k, v in e.items() if k not in STAMPS},
            "tags": sorted(e["tags"]),
        }
        for e in bundle["entries"]
    }
    types = {t["key"]: {**t, "tint": ""} for t in bundle["types"]}
    assets = {a["path"]: a for a in bundle["assets"]}
    return types, entries, assets, bundle["profile"], bundle["links"]


@pytest.mark.parametrize("name", DEMOS)
def test_demo_exports_as_it_was_written(name, tmp_path):
    services = Services()
    services.content_import.load_demo(name)

    summary = services.content_export.export(tmp_path)

    demo = ContentFilesStore().read_demo(name)
    exported = ContentFilesStore().read(tmp_path)
    for got, expected in zip(_by_key(exported), _by_key(demo), strict=True):
        assert got == expected
    assert (summary.types, summary.entries, summary.assets) == (
        len(demo["types"]),
        len(demo["entries"]),
        len(demo["assets"]),
    )


@pytest.mark.parametrize("name", DEMOS)
def test_export_imports_back_to_identical_files(name, tmp_path):
    services = Services()
    services.content_import.load_demo(name)
    services.content_export.export(tmp_path / "first")

    services.content_import.import_from(tmp_path / "first")
    services.content_export.export(tmp_path / "second")

    comparison = filecmp.dircmp(tmp_path / "first", tmp_path / "second")
    assert _differences(comparison) == []


def _differences(comparison):
    found = [
        *comparison.left_only,
        *comparison.right_only,
        *comparison.diff_files,
        *comparison.funny_files,
    ]
    for sub in comparison.subdirs.values():
        found.extend(_differences(sub))
    return found
