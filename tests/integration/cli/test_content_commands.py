from io import StringIO

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command, load_command_class
from django.core.management.base import CommandError

from lapidarium.links.content_files.markdown import ContentFilesStore
from lapidarium.links.db.django.models import Entry, EntryType, Relation
from lapidarium.pacts.content import BundleValidationError

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]

UNKNOWN_DEMO = "Demo 'photography': not one of dev, ttrpg"


def _run(*args):
    out = StringIO()
    call_command(*args, stdout=out)
    return out.getvalue()


def test_import_loads_the_named_demo():
    output = _run("import_content", "--demo", "ttrpg")

    assert output == "Imported 9 types, 13 entries, 3 assets.\n"
    assert EntryType.objects.count() == 9
    assert Entry.objects.filter(type__key="session").count() == 2


def test_import_names_the_bundled_demos_for_an_unknown_one():
    with pytest.raises(CommandError, match=UNKNOWN_DEMO):
        call_command("import_content", "--demo", "photography")


def test_import_refuses_a_path_together_with_a_demo(tmp_path):
    with pytest.raises(CommandError, match="not allowed with"):
        call_command("import_content", str(tmp_path), "--demo", "dev")
    assert not EntryType.objects.exists()


def test_import_needs_a_path_or_a_demo():
    with pytest.raises(CommandError, match="one of the arguments"):
        call_command("import_content")


@pytest.mark.parametrize("command", ("import_content", "setup_local"))
def test_help_builds_no_services(command, settings):
    settings.SERVICES_FACTORY = "lapidarium.missing.Services"

    load_command_class("lapidarium.gates.cli.django", command).create_parser(
        "manage.py", command
    )


def test_export_then_import(tmp_path, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        _run("import_content", "--demo", "dev")

    exported = _run("export_content", str(tmp_path))
    with django_capture_on_commit_callbacks(execute=True):
        imported = _run("import_content", str(tmp_path))

    assert exported == "Exported 6 types, 8 entries, 2 assets.\n"
    assert imported == "Imported 6 types, 8 entries, 2 assets.\n"


def test_import_reports_an_invalid_bundle(tmp_path):
    with pytest.raises(CommandError, match=r"lapidarium\.yaml"):
        call_command("import_content", str(tmp_path))


def test_import_reports_a_broken_demo(monkeypatch):
    def broken(_store, _name):
        raise BundleValidationError({"types/session.yaml": ["Broken."]})

    monkeypatch.setattr(ContentFilesStore, "read_demo", broken)

    with pytest.raises(CommandError, match=r"types/session\.yaml: Broken\."):
        call_command("import_content", "--demo", "dev")


def test_export_reports_a_published_link_to_a_draft(tmp_path):
    _run("import_content", "--demo", "dev")
    relation = Relation.objects.first()
    Entry.objects.filter(pk=relation.to_entry_id).update(status="draft")

    with pytest.raises(CommandError, match=r"Links to the draft"):
        call_command("export_content", str(tmp_path))


def test_setup_local_loads_a_demo_and_a_login(settings):
    settings.DEBUG = True

    first = _run("setup_local", "--demo", "dev")
    again = _run("setup_local", "--demo", "dev", "--password", "changed")

    loaded = "Loaded 6 types, 8 entries, 2 assets."
    assert first == f"{loaded} Created superuser 'admin'.\n"
    assert again == f"{loaded} Reset superuser 'admin'.\n"
    assert EntryType.objects.count() == 6
    assert User.objects.get(username="admin").check_password("changed")


def test_setup_local_refuses_without_debug(settings):
    settings.DEBUG = False

    with pytest.raises(CommandError, match="only with DEBUG on"):
        call_command("setup_local")
    assert not User.objects.exists()


def test_setup_local_names_the_bundled_demos_for_an_unknown_one(settings):
    settings.DEBUG = True

    with pytest.raises(CommandError, match=UNKNOWN_DEMO):
        call_command("setup_local", "--demo", "photography")
    assert not User.objects.exists()


def test_setup_local_reports_a_broken_set(settings, monkeypatch):
    settings.DEBUG = True

    def broken(_store, _name):
        raise BundleValidationError({"types/session.yaml": ["Broken."]})

    monkeypatch.setattr(ContentFilesStore, "read_demo", broken)

    with pytest.raises(CommandError, match=r"types/session\.yaml: Broken\."):
        call_command("setup_local")
