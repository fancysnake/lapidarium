"""A failed import leaves media storage exactly as it found it."""

import pytest
from django.db import IntegrityError

from lapidarium.inits import Services
from lapidarium.links.content_files.markdown import ContentFilesStore
from lapidarium.links.db.django.repositories import ProfileRepository

pytestmark = [pytest.mark.django_db]


def _snapshot(root):
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _fail(*_args, **_kwargs):
    raise IntegrityError


def test_failed_import_leaves_media_as_it_was(
    demo, monkeypatch, *, django_capture_on_commit_callbacks
):
    before = _snapshot(demo)
    bundle = ContentFilesStore().read_demo("ttrpg")
    first, *rest = bundle["assets"]
    bundle["assets"] = [
        {**first, "content": b"<svg/>"},
        *rest,
        {"path": "assets/new.svg", "alt": "", "content": b"<svg/>"},
    ]
    monkeypatch.setattr(ContentFilesStore, "read_demo", lambda _store, _name: bundle)
    monkeypatch.setattr(ProfileRepository, "replace_links", _fail)

    with (
        django_capture_on_commit_callbacks(execute=True),
        pytest.raises(IntegrityError),
    ):
        Services().content_import.load_demo("ttrpg")

    assert _snapshot(demo) == before
