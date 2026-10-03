import datetime as dt

import pytest

from lapidarium.links.content_files.markdown import ContentFilesStore
from lapidarium.pacts import BundleValidationError, NotFoundError

ENTRY = """---
title: Moose
summary: One sentence.
date: 2026-03-14
status: published
tags: [sci-fi]
metadata:
  system: Mothership
parts:
  - kind: text
  - kind: image
    asset: assets/moose.svg
  - kind: text
relations:
  - role: part_of
    to: project/saga
---
First section.

<!-- part -->

Second section.
"""


@pytest.fixture(name="bundle_dir")
def bundle_dir_fixture(tmp_path):
    (tmp_path / "lapidarium.yaml").write_text("format: 1\n", encoding="utf-8")
    (tmp_path / "types").mkdir()
    (tmp_path / "types" / "session.yaml").write_text(
        "key: session\nlabel: Session\nlabel_plural: Sessions\nroute: sessions\n"
        "allowed_parts: [text, image]\n"
        "fields:\n  - {key: system, label: System, kind: text}\n",
        encoding="utf-8",
    )
    (tmp_path / "content" / "session").mkdir(parents=True)
    (tmp_path / "content" / "session" / "moose.md").write_text(ENTRY, encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "moose.svg").write_bytes(b"<svg/>")
    (tmp_path / "assets.yaml").write_text(
        "- {path: assets/moose.svg, alt: A moose}\n", encoding="utf-8"
    )
    return tmp_path


def test_demos_are_listed_and_unknown_ones_refused():
    store = ContentFilesStore()

    assert store.demo_names() == ("dev", "ttrpg")
    with pytest.raises(NotFoundError):
        store.read_demo("photography")


def test_read_fills_defaults_and_splits_the_body_into_text_parts(bundle_dir):
    bundle = ContentFilesStore().read(bundle_dir)

    assert bundle["profile"] is None
    assert not bundle["links"]
    assert bundle["assets"] == [
        {"path": "assets/moose.svg", "alt": "A moose", "content": b"<svg/>"}
    ]
    assert len(bundle["types"]) == 1
    entry_type = bundle["types"][0]
    assert entry_type["role"] == "thing"
    assert not entry_type["tint"]
    assert entry_type["fields"][0]["url_kind"] == "any"
    assert len(bundle["entries"]) == 1
    entry = bundle["entries"][0]
    assert entry["type"] == "session"
    assert entry["slug"] == "moose"
    assert entry["date"] == dt.date(2026, 3, 14)
    assert entry["featured"] is False
    assert [(p["kind"], p["text"], p["asset"]) for p in entry["parts"]] == [
        ("text", "First section.", ""),
        ("image", "", "assets/moose.svg"),
        ("text", "Second section.", ""),
    ]
    assert entry["relations"] == [
        {"role": "part_of", "target_type": "project", "target_slug": "saga"}
    ]


def test_write_produces_what_read_parses(bundle_dir, tmp_path_factory):
    store = ContentFilesStore()
    bundle = store.read(bundle_dir)
    target = tmp_path_factory.mktemp("export")
    (target / "content" / "session").mkdir(parents=True)
    (target / "content" / "session" / "deleted.md").write_text("stale")
    (target / ".git").mkdir()

    store.write(target, bundle)

    assert store.read(target) == bundle
    assert not (target / "content" / "session" / "deleted.md").exists()
    assert (target / ".git").exists()
    assert not (target / "profile.yaml").exists()
    written = (target / "content" / "session" / "moose.md").read_text(encoding="utf-8")
    assert written == (
        "---\n"
        "title: Moose\n"
        "summary: One sentence.\n"
        "date: 2026-03-14\n"
        "status: published\n"
        "tags:\n"
        "- sci-fi\n"
        "metadata:\n"
        "  system: Mothership\n"
        "parts:\n"
        "- kind: text\n"
        "- kind: image\n"
        "  asset: assets/moose.svg\n"
        "- kind: text\n"
        "relations:\n"
        "- role: part_of\n"
        "  to: project/saga\n"
        "---\n"
        "\n"
        "First section.\n"
        "\n"
        "<!-- part -->\n"
        "\n"
        "Second section.\n"
    )
    assert (target / "types" / "session.yaml").read_text(encoding="utf-8") == (
        "key: session\n"
        "label: Session\n"
        "label_plural: Sessions\n"
        "route: sessions\n"
        "allowed_parts:\n"
        "- text\n"
        "- image\n"
        "fields:\n"
        "- key: system\n"
        "  label: System\n"
        "  kind: text\n"
    )


def test_read_requires_format_one(tmp_path):
    (tmp_path / "lapidarium.yaml").write_text("format: 2\n", encoding="utf-8")

    with pytest.raises(BundleValidationError) as caught:
        ContentFilesStore().read(tmp_path)

    assert caught.value.errors == {"lapidarium.yaml": ["Expected format 1."]}


def test_read_requires_a_manifest(tmp_path):
    with pytest.raises(BundleValidationError) as caught:
        ContentFilesStore().read(tmp_path)

    assert list(caught.value.errors) == ["lapidarium.yaml"]


def test_read_reports_every_broken_file(bundle_dir):
    (bundle_dir / "profile.yaml").write_text("handle: nameless\n", encoding="utf-8")
    (bundle_dir / "types" / "song.yaml").write_text(
        "key: song\nlabel: Song\nlabel_plural: Songs\nroute: songs\nrole: jukebox\n",
        encoding="utf-8",
    )
    content = bundle_dir / "content" / "session"
    (content / "bare.md").write_text("Just text.\n", encoding="utf-8")
    (content / "count.md").write_text(
        "---\ntitle: T\nsummary: S\nparts:\n  - kind: text\n---\n", encoding="utf-8"
    )
    (bundle_dir / "assets.yaml").write_text(
        "- {path: ../secret.txt, alt: ''}\n", encoding="utf-8"
    )

    with pytest.raises(BundleValidationError) as caught:
        ContentFilesStore().read(bundle_dir)

    assert caught.value.errors == {
        "profile.yaml": ["name: Field required"],
        "types/song.yaml": [
            (
                "role: Input should be 'thing', 'container_outcome',"
                " 'container_timespan' or 'calendar'"
            )
        ],
        "content/session/bare.md": ["Expected YAML frontmatter between --- lines."],
        "content/session/count.md": ["1 text parts listed, 0 in the body."],
        "assets.yaml": ["Asset paths stay under assets/, got '../secret.txt'."],
    }


def test_read_of_an_empty_bundle(tmp_path):
    (tmp_path / "lapidarium.yaml").write_text("format: 1\n", encoding="utf-8")

    assert ContentFilesStore().read(tmp_path) == {
        "profile": None,
        "links": [],
        "types": [],
        "entries": [],
        "assets": [],
    }
