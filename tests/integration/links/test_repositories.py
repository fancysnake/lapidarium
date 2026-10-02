import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError

from lapidarium.links.db.django.models import (
    Entry,
    EntryType,
    ExternalItem,
    FieldDefinition,
    Link,
    MediaAsset,
    Profile,
)
from lapidarium.links.db.django.repositories import (
    AccountRepository,
    EntryRepository,
    MediaAssetRepository,
    ProfileRepository,
)
from lapidarium.pacts import FIELD_DEFAULTS, TYPE_DEFAULTS, NotFoundError
from tests.factories import entry_data

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


@pytest.mark.usefixtures("demo")
def test_set_relations_refuses_a_missing_end():
    with pytest.raises(NotFoundError, match="session/nope"):
        EntryRepository().set_relations("session", "nope", relations=[])
    with pytest.raises(NotFoundError, match="project/gone"):
        EntryRepository().set_relations(
            "session",
            "bal-w-zamku",
            relations=[
                {"role": "part_of", "target_type": "project", "target_slug": "gone"}
            ],
        )


@pytest.mark.usefixtures("demo")
def test_entries_refuse_an_unknown_cover():
    data = entry_data("bal-w-zamku", cover="assets/missing.png")

    with pytest.raises(NotFoundError, match=r"assets/missing\.png"):
        EntryRepository().save(data)


@pytest.mark.usefixtures("demo")
def test_search_text_holds_what_a_visitor_might_look_for():
    entry = Entry.objects.get(slug="ucieczka-przed-kosmicznym-losiem")

    assert entry.search_text.splitlines() == [
        "Ucieczka przed kosmicznym łosiem",
        "Załoga frachtowca odkrywa, że ładownia nie jest pusta, a łoś nie jest zwykły.",
        "Mothership",
        "one-shot",
        "Ania, Bartek, Celina",
        "one-shot",
        "sci-fi",
        (
            "Zaczęło się od rutynowego kursu na stację Tycho. Zanim ktokolwiek zdążył"
            " sprawdzić"
        ),
        "manifest, w ładowni coś zaryczało.",
        "",
        (
            "Po trzech godzinach i dwóch śluzach załoga uciekła kapsułą, a łoś przejął"
            " statek."
        ),
        "Nagranie całej sesji",
    ]


@pytest.mark.usefixtures("demo")
def test_saving_an_asset_again_replaces_its_file():
    MediaAssetRepository().save(
        {"path": "assets/demo/los.svg", "alt": "New alt", "content": b"<svg/>"}
    )

    asset = MediaAsset.objects.get(file="assets/demo/los.svg")
    assert asset.alt == "New alt"
    assert MediaAssetRepository().read("assets/demo/los.svg") == b"<svg/>"


@pytest.mark.usefixtures("demo")
def test_saving_the_profile_again_updates_the_one_row():
    ProfileRepository().save(
        dict.fromkeys(("bio", "email", "handle", "photo", "tagline"), "")
        | {"name": "Mira K."}
    )

    assert Profile.objects.get().name == "Mira K."
    assert ProfileRepository().get().photo is None


def test_no_profile_yet():
    assert ProfileRepository().get() is None


def test_models_read_as_their_names():

    assert str(Profile(name="Mira")) == "Mira"
    assert str(Link(label="itch.io")) == "itch.io"
    assert str(ExternalItem(title="New video")) == "New video"


@pytest.mark.usefixtures("demo")
def test_an_entry_cannot_end_before_it_starts():

    event = Entry.objects.get(slug="pyrkon-2027")
    event.end_at = event.start_at.replace(year=2026)

    with pytest.raises(IntegrityError):
        event.save()


def _listed(defaults):
    return {k: list(v) if isinstance(v, tuple) else v for k, v in defaults.items()}


def test_new_types_and_fields_take_the_shared_defaults():
    entry_type, field = EntryType(), FieldDefinition()

    assert {k: getattr(entry_type, k) for k in TYPE_DEFAULTS} == _listed(TYPE_DEFAULTS)
    settings = {k: v for k, v in FIELD_DEFAULTS.items() if k != "target_type"}
    assert {k: getattr(field, k) for k in settings} == _listed(settings)
    assert field.target_type is None


def test_ensure_superuser_creates_then_resets_the_login():
    repository = AccountRepository()

    assert repository.ensure_superuser("admin", password="first") is True
    User.objects.filter(username="admin").update(is_active=False, is_staff=False)
    assert repository.ensure_superuser("admin", password="second") is False

    user = User.objects.get(username="admin")
    assert (user.is_active, user.is_staff, user.is_superuser) == (True, True, True)
    assert user.check_password("second")
