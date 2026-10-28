import datetime as dt
import io

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.db import IntegrityError
from django.utils import translation
from PIL import Image

from lapidarium.links.db.django.models import (
    Entry,
    EntryType,
    ExternalItem,
    FieldDefinition,
    Friend,
    Link,
    MediaAsset,
    Profile,
)
from lapidarium.links.db.django.repositories import (
    AccountRepository,
    EntryRepository,
    EntryTypeRepository,
    ExternalItemRepository,
    MediaAssetRepository,
    ProfileRepository,
)
from lapidarium.pacts import (
    BUILTIN_DEFAULTS,
    BUTTON_SIZE,
    FIELD_DEFAULTS,
    TYPE_DEFAULTS,
    DoorPick,
    EntryTypeDTO,
    ExternalItemDTO,
    FieldKind,
    Layout,
    NotFoundError,
    Outcome,
    PartKind,
    TypeRole,
    UrlKind,
)
from tests.factories import (
    NOW,
    entry_data,
    field_data,
    part_data,
    profile_data,
    type_data,
)

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
def test_saving_an_asset_again_updates_its_row_only():
    before = MediaAssetRepository().read("assets/demo/los.svg")

    MediaAssetRepository().save(
        {"path": "assets/demo/los.svg", "alt": "New alt", "content": b"<svg/>"}
    )

    asset = MediaAsset.objects.get(file="assets/demo/los.svg")
    assert asset.alt == "New alt"
    assert MediaAssetRepository().read("assets/demo/los.svg") == before


@pytest.mark.usefixtures("demo")
def test_writing_an_asset_again_replaces_its_file():
    MediaAssetRepository().write("assets/demo/los.svg", content=b"<svg/>")

    assert MediaAssetRepository().read("assets/demo/los.svg") == b"<svg/>"


def test_writing_refuses_a_name_the_storage_changed(media_root, monkeypatch):
    monkeypatch.setattr(
        FileSystemStorage,
        "get_available_name",
        lambda *_args, **_kwargs: "assets/other.svg",
    )

    with pytest.raises(OSError, match=r"assets/other\.svg"):
        MediaAssetRepository().write("assets/new.svg", content=b"<svg/>")

    assert not (media_root / "assets" / "other.svg").exists()


@pytest.mark.usefixtures("demo")
def test_saving_the_profile_again_updates_the_one_row():
    ProfileRepository().save(profile_data(name="Mira K."))

    assert Profile.objects.get().name == "Mira K."
    assert ProfileRepository().get().photo is None


def test_no_profile_yet():
    assert ProfileRepository().get() is None


def test_models_read_as_their_names():

    assert str(Profile(name="Mira")) == "Mira"
    assert str(Link(label="itch.io")) == "itch.io"
    assert str(Friend(name="Ada")) == "Ada"
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


def _off_default(data, defaults):
    return all(data[k] != v for k, v in _listed(defaults).items())


def test_entry_types_read_back_every_column_they_save():
    field = field_data(
        "system",
        FieldKind.RELATION,
        label="Game system",
        required=True,
        choices=["Mothership"],
        url_kind=UrlKind.ITCH,
        target_type="project",
        show_on_card=True,
        show_in_metadata_panel=False,
    )
    data = type_data(
        label="Session",
        label_plural="Sessions",
        route="plays",
        colour="#123456",
        tint="#abcdef",
        icon="dice",
        order=3,
        in_menu=False,
        role=TypeRole.CALENDAR,
        layout=Layout.GALLERY,
        allowed_parts=[PartKind.VIDEO, PartKind.LINK],
        required_parts=[PartKind.VIDEO],
        door_enabled=True,
        door_label="Play",
        door_pick=DoorPick.UPCOMING,
        door_min_entries=4,
        list_filters=["system"],
        has_detail_page=False,
        fields=[field],
    )
    assert _off_default(data, TYPE_DEFAULTS)
    assert _off_default(field, FIELD_DEFAULTS)

    EntryTypeRepository().save_all([type_data("project"), data])

    saved = {t.key: t for t in EntryTypeRepository().list_all()}["session"]
    assert saved.model_dump() == EntryTypeDTO(**data).model_dump()


def test_entries_read_back_every_column_they_save():
    EntryTypeRepository().save_all([type_data()])
    MediaAssetRepository().save({"path": "assets/los.png", "alt": "", "content": b""})
    data = entry_data(
        title="Moose",
        summary="It escaped.",
        external_url="https://example.com/moose",
        featured=True,
        hide_from_whats_new=True,
        license="CC-BY-4.0",
        cover="assets/los.png",
        metadata={"system": "Mothership"},
        date=dt.date(2026, 5, 1),
        start_at=NOW,
        end_at=NOW + dt.timedelta(hours=4),
        location="Kraków",
        is_online=True,
        outcome=Outcome.FINISHED,
        tags=["sci-fi"],
        parts=[
            part_data(
                PartKind.IMAGE,
                text="Body",
                url="https://example.com/los",
                asset="assets/los.png",
                caption="The moose",
                options={"fit": "cover"},
            )
        ],
        syndication=[{"platform": "itch.io", "url": "https://mira.itch.io/moose"}],
        created_at=NOW - dt.timedelta(days=2),
        updated_at=NOW - dt.timedelta(days=1),
    )
    assert _off_default(data, BUILTIN_DEFAULTS)

    EntryRepository().save(data)

    (entry,) = EntryRepository().list_published()
    saved = entry.model_dump()
    nested = {"cover", "parts", "relations", "syndication", "tags"}
    columns = (data.keys() & saved.keys()) - nested
    assert {k: saved[k] for k in columns} == {k: data[k] for k in columns}
    assert entry.cover.path == data["cover"]
    assert list(entry.tags) == data["tags"]
    parts = [part | {"asset": part["asset"]["path"]} for part in saved["parts"]]
    assert parts == data["parts"]
    assert list(saved["syndication"]) == data["syndication"]


def test_the_profile_reads_back_every_column_it_saves():
    for path in ("assets/mira.png", "assets/mira-88.png"):
        MediaAssetRepository().save({"path": path, "alt": "", "content": b""})
    data = {
        "name": "Mira",
        "handle": "@mira",
        "tagline": "Makes small games.",
        "photo": "assets/mira.png",
        "bio": "Hello.",
        "email": "mira@example.com",
        "button": "assets/mira-88.png",
        "friends_title": "Table friends",
        "friends_intro": "People I play with.",
    }
    links = [
        {"platform": "youtube", "url": "https://youtube.com/@mira", "label": "Videos"},
        {"platform": "itch", "url": "https://mira.itch.io", "label": "Games"},
    ]

    ProfileRepository().save(data)
    ProfileRepository().replace_links(links)

    saved = ProfileRepository().get().model_dump()
    assets = {"photo": saved["photo"]["path"], "button": saved["button"]["path"]}
    assert saved | assets == data
    columns = ("order", *links[0])
    assert list(Link.objects.order_by("order").values(*columns)) == [
        {"order": order} | link for order, link in enumerate(links)
    ]


def test_friends_read_back_in_the_order_saved():
    MediaAssetRepository().save({"path": "assets/ada.png", "alt": "", "content": b""})
    friends = [
        {"name": "Ada", "url": "https://ada.example.org", "button": "assets/ada.png"},
        {"name": "Bo", "url": "https://bo.example.org", "button": ""},
    ]
    ProfileRepository().replace_friends([{**friends[1], "name": "Gone"}])

    ProfileRepository().replace_friends(friends)

    saved = [f.model_dump() for f in ProfileRepository().list_friends()]
    assert [
        f | {"button": f["button"]["path"] if f["button"] else ""} for f in saved
    ] == (friends)
    assert list(Friend.objects.values_list("order", flat=True)) == [0, 1]


def _png(size):
    image = io.BytesIO()
    Image.new("RGB", size).save(image, format="PNG")
    return image.getvalue()


def test_a_button_of_88_by_31_is_valid():
    asset = MediaAsset.objects.create(file=ContentFile(_png(BUTTON_SIZE), name="b.png"))

    Friend(name="Ada", url="https://ada.example.org", button=asset).full_clean()


@pytest.mark.parametrize(
    ("content", "missing"),
    ((_png((88, 32)), False), (b"<svg/>", False), (_png(BUTTON_SIZE), True)),
)
def test_a_button_must_be_an_88_by_31_image(content, *, missing):
    asset = MediaAsset.objects.create(file=ContentFile(content, name="b.png"))
    if missing:
        asset.file.storage.delete(asset.file.name)
    friend = Friend(name="Ada", url="https://ada.example.org", button=asset)

    with translation.override("en"):
        with pytest.raises(ValidationError) as caught:
            friend.full_clean()

        assert caught.value.message_dict == {"button": ["A button is an 88x31 image."]}


def test_ensure_superuser_creates_then_resets_the_login():
    repository = AccountRepository()

    assert repository.ensure_superuser("admin", password="first") is True
    User.objects.filter(username="admin").update(is_active=False, is_staff=False)
    assert repository.ensure_superuser("admin", password="second") is False

    user = User.objects.get(username="admin")
    assert (user.is_active, user.is_staff, user.is_superuser) == (True, True, True)
    assert user.check_password("second")


@pytest.mark.usefixtures("demo")
def test_search_finds_published_entries_holding_every_term():
    found = EntryRepository().search(["Tycho", "rutynowego"], limit=10)

    assert [e.slug for e in found] == ["ucieczka-przed-kosmicznym-losiem"]
    assert EntryRepository().search(["Tycho", "nope"], limit=10) == []
    assert len(EntryRepository().search(["a"], limit=2)) == 2


def test_recent_external_items_leave_out_those_an_entry_speaks_for():
    when = dt.datetime(2026, 10, 1, tzinfo=dt.UTC)
    for index in range(3):
        ExternalItem.objects.create(
            source="YouTube",
            external_id=str(index),
            title=f"Video {index}",
            url=f"https://youtu.be/{index}",
            published_at=when + dt.timedelta(days=index),
        )
    linked = ExternalItem.objects.get(external_id="2")
    linked.entry = Entry.objects.create(
        type=EntryType.objects.create(key="talk", route="talks"),
        slug="talk",
        title="Talk",
        summary="One.",
    )
    linked.save()

    items = ExternalItemRepository().list_recent(1)

    assert items == [
        ExternalItemDTO(
            source="YouTube",
            title="Video 1",
            url="https://youtu.be/1",
            published_at=when + dt.timedelta(days=1),
        )
    ]
