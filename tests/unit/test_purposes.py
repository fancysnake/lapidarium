from unittest.mock import MagicMock

import pytest

from lapidarium.mills.content import type_to_data
from lapidarium.mills.purposes import PurposeService
from lapidarium.pacts.content import FieldKind, NotFoundError, PartKind, TypeRole
from lapidarium.pacts.purposes import TypeValidationError
from lapidarium.specs import MECHANIC_NAMES, PURPOSES
from tests.factories import schema_service, type_dto


def _service(types):
    return PurposeService(types=types, schema=schema_service())


def _new_type(**overrides):
    return {
        "key": "",
        "label": "Volunteering",
        "label_plural": "Volunteering",
        "route": "volunteering",
        "colour": "#6b3fa0",
        "fields": {"organisation": "Organisation", "position": "Role"},
        "allowed_parts": list(PartKind),
        "required_parts": [],
        "in_menu": True,
        "has_detail_page": True,
        "door_enabled": False,
        **overrides,
    }


def test_every_role_has_a_name_and_a_purpose():
    assert (
        set(MECHANIC_NAMES) == {purpose.role for purpose in PURPOSES} == set(TypeRole)
    )


def test_overview_groups_types_by_role_with_counts_and_containment():
    song = type_dto("song")
    meme = type_dto("meme")
    album = type_dto("album", role=TypeRole.CONTAINER_OUTCOME)
    types = MagicMock()
    types.list_all.return_value = [song, meme, album]
    types.entry_counts.return_value = {"song": 3, "meme": 0, "album": 1}
    types.containment.return_value = {("song", "album")}

    overview = _service(types).overview()

    assert [(m.role, m.name) for m in overview] == list(MECHANIC_NAMES.items())
    by_role = {m.role: m for m in overview}
    assert [
        (use.entry_type, use.entries, use.containers, use.contents)
        for use in by_role[TypeRole.THING].types
    ] == [(song, 3, (album,), ()), (meme, 0, (), ())]
    assert [
        (use.entry_type, use.entries, use.containers, use.contents)
        for use in by_role[TypeRole.CONTAINER_OUTCOME].types
    ] == [(album, 1, (), (song,))]
    assert by_role[TypeRole.CALENDAR].types == ()
    assert [p.key for p in by_role[TypeRole.CONTAINER_TIMESPAN].purposes] == [
        "job",
        "volunteering",
        "craft",
        "skill",
    ]


def test_purpose_is_found_by_key():
    service = _service(MagicMock())

    assert service.purpose("job").role == TypeRole.CONTAINER_TIMESPAN
    with pytest.raises(NotFoundError):
        service.purpose("hobby")


def test_create_saves_a_type_on_the_purposes_role_after_the_others():
    types = MagicMock()
    types.list_all.return_value = [type_dto("song", order=4)]

    created = _service(types).create("volunteering", _new_type())

    assert (created.key, created.role, created.order, created.tint) == (
        "volunteering",
        TypeRole.CONTAINER_TIMESPAN,
        5,
        "#ede8f4",
    )
    assert [(f.key, f.label, f.kind) for f in created.fields] == [
        ("organisation", "Organisation", FieldKind.TEXT),
        ("position", "Role", FieldKind.TEXT),
    ]
    assert created.allowed_parts == tuple(PartKind)
    types.save_all.assert_called_once_with([type_to_data(created)])


def test_plan_derives_the_key_and_drops_fields_left_out_without_saving():
    types = MagicMock()
    types.list_all.return_value = []

    planned = _service(types).plan(
        "job",
        _new_type(label="Day job!", route="day-jobs", fields={"employer": "Company"}),
    )

    assert (planned.key, planned.order) == ("day_job", 0)
    assert [(f.key, f.label) for f in planned.fields] == [("employer", "Company")]
    types.save_all.assert_not_called()


def test_create_refuses_a_type_that_breaks_the_rules():
    types = MagicMock()
    types.list_all.return_value = [type_dto("song"), type_dto("talk", route="about")]

    with pytest.raises(TypeValidationError) as caught:
        _service(types).create(
            "work",
            _new_type(
                key="song",
                route="about",
                colour="#ffff00",
                fields={},
                allowed_parts=[PartKind.TEXT],
                required_parts=[PartKind.IMAGE],
            ),
        )

    assert caught.value.messages == (
        "Contrast with the page background is 1.07:1, needs 4.5:1.",
        "Contrast with the tint is 1.06:1, needs 4.5:1.",
        "/about/ belongs to the about page.",
        "Required parts must be allowed.",
        "A type with the key 'song' already exists.",
        "/about/ already lists Talks.",
    )
    types.save_all.assert_not_called()


def test_create_refuses_a_name_no_key_can_be_made_from():
    types = MagicMock()
    types.list_all.return_value = []

    with pytest.raises(TypeValidationError) as caught:
        _service(types).create("work", _new_type(label="???", fields={}))

    assert caught.value.messages == ("Key '' may hold only letters, digits, - and _.",)
