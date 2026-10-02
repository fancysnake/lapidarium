from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from lapidarium.links.content_files.markdown import ContentFilesStore
from lapidarium.links.db.django.models import Entry, EntryType, Relation
from lapidarium.pacts import BundleValidationError

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


def _run(*args):
    out = StringIO()
    call_command(*args, stdout=out)
    return out.getvalue()


def test_load_demo_loads_the_named_set():
    output = _run("load_demo", "ttrpg")

    assert output == "Loaded 9 types, 13 entries, 3 assets.\n"
    assert EntryType.objects.count() == 9
    assert Entry.objects.filter(type__key="session").count() == 2


def test_load_demo_offers_only_bundled_sets():
    with pytest.raises(CommandError, match="invalid choice: 'photography'"):
        call_command("load_demo", "photography")


def test_export_then_import(tmp_path):
    _run("load_demo", "dev")

    exported = _run("export_content", str(tmp_path))
    imported = _run("import_content", str(tmp_path))

    assert exported == "Exported 6 types, 8 entries, 2 assets.\n"
    assert imported == "Imported 6 types, 8 entries, 2 assets.\n"


def test_import_reports_an_invalid_bundle(tmp_path):
    with pytest.raises(CommandError, match=r"lapidarium\.yaml"):
        call_command("import_content", str(tmp_path))


def test_load_demo_reports_a_broken_set(monkeypatch):
    def broken(_store, _name):
        raise BundleValidationError({"types/session.yaml": ["Broken."]})

    monkeypatch.setattr(ContentFilesStore, "read_demo", broken)

    with pytest.raises(CommandError, match=r"types/session\.yaml: Broken\."):
        call_command("load_demo", "dev")


def test_export_reports_a_published_link_to_a_draft(tmp_path):
    _run("load_demo", "dev")
    relation = Relation.objects.first()
    Entry.objects.filter(pk=relation.to_entry_id).update(status="draft")

    with pytest.raises(CommandError, match=r"Links to the draft"):
        call_command("export_content", str(tmp_path))
