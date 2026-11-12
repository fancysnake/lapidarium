from unittest.mock import MagicMock

import pytest

from lapidarium.mills.content import type_to_data
from lapidarium.mills.purposes import PurposeService
from lapidarium.pacts.content import FieldKind, NotFoundError, PartKind, TypeRole
from lapidarium.pacts.purposes import TypeChangeData, TypeEffect, TypeValidationError
from lapidarium.specs import MECHANIC_NAMES, PURPOSES
from tests.factories import field_dto, schema_service, type_dto


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


def _change(entry_type, **overrides):
    """Return a change that leaves the type as it is, but for `overrides`."""
    stored = type_to_data(entry_type)
    return {
        **{key: stored[key] for key in TypeChangeData.__annotations__ if key in stored},
        "fields": {field.key: field.label for field in entry_type.fields},
        "added": {},
        **overrides,
    }


def _types_with(entry_type, *others, entries=0, holders=None):
    types = MagicMock()
    types.list_all.return_value = [entry_type, *others]
    types.entry_counts.return_value = {entry_type.key: entries}
    types.part_holders.return_value = holders or {}
    return types


def test_entry_type_is_found_by_key():
    song = type_dto("song")
    service = _service(_types_with(song))

    assert service.entry_type("song") == song
    with pytest.raises(NotFoundError):
        service.entry_type("album")


def test_plan_change_relabels_adds_a_field_and_keeps_the_rest_without_saving():
    song = type_dto(
        "song",
        fields=[field_dto("album", FieldKind.CHOICE, choices=["Moose"])],
        tint="#fafafa",
        order=7,
    )
    types = _types_with(song)

    planned = _service(types).plan_change(
        "song",
        _change(
            song,
            label="Tune",
            fields={"album": "Record"},
            added={"Year out": FieldKind.NUMBER},
        ),
    )

    changed = planned.entry_type
    assert (planned.effects, planned.saved, planned.consent) == ((), False, "")
    assert (changed.key, changed.label, changed.order, changed.tint) == (
        "song",
        "Tune",
        7,
        "#fafafa",
    )
    assert [(f.key, f.label, f.kind, f.choices) for f in changed.fields] == [
        ("album", "Record", FieldKind.CHOICE, ("Moose",)),
        ("year_out", "Year out", FieldKind.NUMBER, ()),
    ]
    types.save_all.assert_not_called()


def test_plan_change_derives_the_tint_of_a_new_colour():
    song = type_dto("song", tint="#fafafa")

    planned = _service(_types_with(song)).plan_change(
        "song", _change(song, colour="#1f5fa8")
    )

    assert planned.entry_type.tint not in {"", "#fafafa"}


def test_plan_change_counts_the_entries_each_change_affects():
    song = type_dto(
        "song", allowed_parts=[PartKind.TEXT, PartKind.IMAGE, PartKind.VIDEO]
    )
    types = _types_with(
        song, entries=12, holders={PartKind.TEXT: 12, PartKind.VIDEO: 3}
    )

    planned = _service(types).plan_change(
        "song",
        _change(
            song,
            route="tunes",
            allowed_parts=[PartKind.TEXT, PartKind.IMAGE, PartKind.AUDIO],
            required_parts=[PartKind.TEXT, PartKind.IMAGE],
        ),
    )

    assert [(e.kind, e.entries, e.part) for e in planned.effects] == [
        (TypeEffect.MOVED, 12, None),
        (TypeEffect.PART_REFUSED, 3, PartKind.VIDEO),
        (TypeEffect.PART_MISSING, 12, PartKind.IMAGE),
    ]
    assert planned.consent == "moved::12,part_refused:video:3,part_missing:image:12"
    types.part_holders.assert_called_once_with("song")


@pytest.mark.parametrize(
    ("before", "after", "effect"),
    ((True, False, TypeEffect.PAGE_LOST), (False, True, TypeEffect.PAGE_GAINED)),
)
def test_plan_change_reports_pages_lost_or_gained_instead_of_moved(
    *, before, after, effect
):
    song = type_dto("song", has_detail_page=before)

    planned = _service(_types_with(song, entries=2)).plan_change(
        "song", _change(song, route="tunes", has_detail_page=after)
    )

    assert [(e.kind, e.entries) for e in planned.effects] == [(effect, 2)]


def test_plan_change_of_a_type_without_entries_has_no_effects():
    song = type_dto("song")
    types = _types_with(song)

    planned = _service(types).plan_change(
        "song", _change(song, route="tunes", allowed_parts=[PartKind.TEXT])
    )

    assert planned.effects == ()
    types.part_holders.assert_not_called()


def test_change_saves_only_with_consent_to_its_effects():
    song = type_dto("song")
    types = _types_with(song, entries=2)
    service = _service(types)
    data = _change(song, route="tunes")

    for consent in ("", "moved::3"):
        refused = service.change("song", data, consent=consent)
        assert (refused.saved, refused.consent) == (False, "moved::2")
    types.save_all.assert_not_called()

    saved = service.change("song", data, consent="moved::2")

    assert saved.saved is True
    assert saved.entry_type.route == "tunes"
    types.save_all.assert_called_once_with([type_to_data(saved.entry_type)])


def test_change_without_effects_needs_no_consent():
    song = type_dto("song")
    types = _types_with(song, entries=2)

    saved = _service(types).change("song", _change(song, label="Tune"), consent="")

    assert saved.saved is True
    types.save_all.assert_called_once_with([type_to_data(saved.entry_type)])


def test_change_refuses_what_the_rules_forbid():
    song = type_dto("song", fields=[field_dto("album")])
    types = _types_with(song, type_dto("talk", route="talks"), entries=2)

    with pytest.raises(TypeValidationError) as caught:
        _service(types).change(
            "song",
            _change(song, route="talks", added={"Album": FieldKind.RELATION}),
            consent="moved::2",
        )

    assert caught.value.messages == (
        "A field with the key 'album' already exists.",
        "A relation field needs settings only the admin has.",
        "/talks/ already lists Talks.",
    )
    types.save_all.assert_not_called()


def test_change_refuses_a_field_name_no_key_can_be_made_from():
    song = type_dto("song")

    with pytest.raises(TypeValidationError) as caught:
        _service(_types_with(song)).change(
            "song", _change(song, added={"???": FieldKind.TEXT}), consent=""
        )

    assert caught.value.messages == (
        "Field key '' may hold only letters, digits, - and _.",
    )


def test_change_of_an_unknown_type_is_not_found():
    song = type_dto("song")

    with pytest.raises(NotFoundError):
        _service(_types_with(song)).plan_change("album", _change(song))
