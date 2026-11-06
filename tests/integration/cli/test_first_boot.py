from io import StringIO

import pytest
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError

from lapidarium.links.content_files.markdown import ContentFilesStore
from lapidarium.links.db.django.models import Entry, EntryType
from lapidarium.pacts.content import BundleValidationError

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]

NO_DEMO = "No demo loaded.\n"
NO_ADMIN = "No superuser created: an account exists or ADMIN_PASSWORD is empty.\n"


@pytest.fixture(name="configured")
def configured_fixture(settings):
    settings.ADMIN_USERNAME = "owner"
    settings.ADMIN_PASSWORD = "first-password"
    settings.DEMO_CONTENT = "dev"
    return settings


def _run():
    out = StringIO()
    call_command("first_boot", stdout=out)
    return out.getvalue()


def test_fresh_database_gets_a_working_login_and_the_demo(configured):
    output = _run()

    assert output == (
        "Loaded 6 types, 8 entries, 2 assets.\nCreated superuser 'owner'.\n"
    )
    user = authenticate(username="owner", password=configured.ADMIN_PASSWORD)
    assert user is not None
    assert user.is_superuser
    assert user.is_staff
    assert EntryType.objects.count() == 6


@pytest.mark.usefixtures("configured")
def test_restart_changes_nothing():
    _run()
    entries = Entry.objects.count()

    output = _run()

    assert output == NO_DEMO + NO_ADMIN
    assert User.objects.count() == 1
    assert Entry.objects.count() == entries


def test_restart_never_changes_the_admin_password(configured):
    _run()
    configured.ADMIN_PASSWORD = "changed-in-the-environment"

    _run()

    assert authenticate(username="owner", password="first-password") is not None


@pytest.mark.usefixtures("configured")
def test_restart_after_the_owner_renames_themselves_adds_no_admin():
    _run()
    User.objects.update(username="renamed")

    _run()

    assert list(User.objects.values_list("username", flat=True)) == ["renamed"]


@pytest.mark.usefixtures("configured")
def test_deleting_every_type_does_not_bring_the_demo_back():
    _run()
    Entry.objects.all().delete()
    EntryType.objects.all().delete()

    _run()

    assert not EntryType.objects.exists()


def test_without_credentials_or_demo_nothing_happens(settings):
    settings.ADMIN_PASSWORD = ""
    settings.DEMO_CONTENT = ""

    assert _run() == NO_DEMO + NO_ADMIN
    assert not User.objects.exists()
    assert not EntryType.objects.exists()


def test_unknown_demo_stops_in_one_line(configured):
    configured.DEMO_CONTENT = "photography"

    with pytest.raises(CommandError, match=r"^DEMO_CONTENT 'photography': not one of"):
        _run()
    assert not User.objects.exists()


@pytest.mark.usefixtures("configured")
def test_broken_demo_stops_in_one_line_and_creates_no_admin(monkeypatch):
    def broken(_store, _name):
        raise BundleValidationError({"types/session.yaml": ["Broken."]})

    monkeypatch.setattr(ContentFilesStore, "read_demo", broken)

    with pytest.raises(CommandError, match=r"types/session\.yaml: Broken\."):
        _run()
    assert not User.objects.exists()
