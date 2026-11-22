from unittest.mock import MagicMock

import pytest

from lapidarium.mills.content import type_to_data
from lapidarium.mills.type_changes import TypeChangeService
from lapidarium.pacts.content import FieldKind, NotFoundError, PartKind
from lapidarium.pacts.purposes import (
    ConsentNeededError,
    FieldsInUseError,
    TypeEffect,
    TypeSettingsData,
    TypeValidationError,
)
from tests.factories import field_dto, ref_dto, schema_service, type_dto


def _service(types):
    return TypeChangeService(types=types, schema=schema_service())


def _change(entry_type, *, labels=None, kinds=None, removed=(), added=None, **settings):
    """Return a change that leaves the type as it is, but for the arguments."""
    stored = type_to_data(entry_type)
    return {
        "settings": {
            **{key: stored[key] for key in TypeSettingsData.__annotations__},
            **settings,
        },
        "labels": labels or {field.key: field.label for field in entry_type.fields},
        "kinds": {f.key: f.kind for f in entry_type.fields} | (kinds or {}),
        "removed": list(removed),
        "added": added,
    }


def _types_with(entry_type, *others, entries=0, holders=None, values=(), linking=()):
    types = MagicMock()
    types.list_all.return_value = [entry_type, *others]
    types.entry_counts.return_value = {entry_type.key: entries}
    types.part_holders.return_value = holders or {}
    types.field_values.return_value = list(values)
    types.linking_entries.return_value = list(linking)
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
            labels={"album": "Record"},
            added={"label": "Year out", "kind": FieldKind.NUMBER},
        ),
    )

    changed = planned.entry_type
    assert (planned.effects, planned.consent) == ((), "")
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
        with pytest.raises(ConsentNeededError) as refused:
            service.change("song", data, consent=consent)
        assert refused.value.change.consent == "moved::2"
    types.save_all.assert_not_called()

    service.change("song", data, consent="moved::2")

    [saved] = types.save_all.call_args.args[0]
    assert saved == type_to_data(song) | {"route": "tunes"}


def test_change_without_effects_needs_no_consent():
    song = type_dto("song")
    types = _types_with(song, entries=2)
    data = _change(song, label="Tune")

    _service(types).change("song", data, consent="")

    [saved] = types.save_all.call_args.args[0]
    assert saved == type_to_data(song) | {"label": "Tune"}
    types.save_all.assert_called_once()


def test_change_refuses_what_the_rules_forbid():
    song = type_dto("song", fields=[field_dto("album")])
    types = _types_with(song, type_dto("talk", route="talks"), entries=2)

    album = {"label": "Album", "kind": FieldKind.RELATION}

    with pytest.raises(TypeValidationError) as caught:
        _service(types).change(
            "song", _change(song, route="talks", added=album), consent="moved::2"
        )

    assert caught.value.messages == (
        "A field with the key 'album' already exists.",
        "A relation field needs settings only the admin has.",
        "/talks/ already lists Talks.",
    )
    types.save_all.assert_not_called()


def test_change_refuses_a_field_name_no_key_can_be_made_from_among_the_rest():
    song = type_dto("song")
    types = _types_with(song, type_dto("talk", route="talks"))
    added = {"label": "???", "kind": FieldKind.TEXT}

    with pytest.raises(TypeValidationError) as caught:
        _service(types).change(
            "song", _change(song, route="talks", added=added), consent=""
        )

    assert caught.value.messages == (
        "No key can be made from '???'; pick another name.",
        "/talks/ already lists Talks.",
    )


def test_change_of_an_unknown_type_is_not_found():
    song = type_dto("song")

    with pytest.raises(NotFoundError):
        _service(_types_with(song)).plan_change("album", _change(song))


def test_change_removes_a_field_no_entry_uses_with_its_list_filter():
    song = type_dto(
        "song",
        fields=[field_dto("album"), field_dto("year")],
        list_filters=["year", "album"],
    )
    types = _types_with(
        song, entries=3, values=[(ref_dto("moose"), ""), (ref_dto("elk"), False)]
    )

    _service(types).change("song", _change(song, removed=["album"]), consent="")

    [saved] = types.save_all.call_args.args[0]
    assert ([f["key"] for f in saved["fields"]], saved["list_filters"]) == (
        ["year"],
        ["year"],
    )
    types.field_values.assert_called_once_with("song", "album")


def test_change_gives_a_field_a_new_kind_without_the_settings_of_the_old_one():
    song = type_dto(
        "song", fields=[field_dto("album", FieldKind.CHOICE, choices=["Moose"])]
    )
    types = _types_with(song)

    _service(types).change(
        "song", _change(song, kinds={"album": FieldKind.TEXT}), consent=""
    )

    [saved] = types.save_all.call_args.args[0]
    assert saved["fields"] == [
        type_to_data(song)["fields"][0] | {"kind": FieldKind.TEXT, "choices": []}
    ]


def test_change_refuses_to_remove_or_re_kind_fields_that_hold_values():
    song = type_dto(
        "song", fields=[field_dto("album"), field_dto("year"), field_dto("live")]
    )
    moose, elk = ref_dto("moose"), ref_dto("elk")
    types = _types_with(song, entries=3, values=[(moose, "Antlers"), (elk, 0)])
    service = _service(types)
    data = _change(song, removed=["album"], kinds={"year": FieldKind.NUMBER})

    for refused_call in (
        lambda: service.plan_change("song", data),
        lambda: service.change("song", data, consent=""),
    ):
        with pytest.raises(FieldsInUseError) as refused:
            refused_call()
        assert [(u.field.key, u.entries) for u in refused.value.uses] == [
            ("album", (moose, elk)),
            ("year", (moose, elk)),
        ]
    types.save_all.assert_not_called()


def test_change_refuses_to_remove_a_relation_field_entries_link_through():
    song = type_dto(
        "song",
        fields=[field_dto("inspired_by", FieldKind.RELATION, target_type="session")],
    )
    moose = ref_dto("moose")
    types = _types_with(song, type_dto(route="sessions"), linking=[moose])
    service = _service(types)

    for change in (
        _change(song, removed=["inspired_by"]),
        _change(song, kinds={"inspired_by": FieldKind.TEXT}),
    ):
        with pytest.raises(FieldsInUseError) as refused:
            service.change("song", change, consent="")
        assert [(u.field.key, u.entries) for u in refused.value.uses] == [
            ("inspired_by", (moose,))
        ]
    types.linking_entries.assert_called_with("song", "inspired_by")
    types.field_values.assert_not_called()
    types.save_all.assert_not_called()


def test_a_rename_is_saved_whatever_the_entries_hold():
    song = type_dto("song", fields=[field_dto("album")])
    types = _types_with(song, entries=1, values=[(ref_dto("moose"), "Antlers")])

    _service(types).change(
        "song", _change(song, labels={"album": "Record"}), consent=""
    )

    [saved] = types.save_all.call_args.args[0]
    assert [(f["key"], f["label"]) for f in saved["fields"]] == [("album", "Record")]
    types.field_values.assert_not_called()


def test_change_refuses_a_kind_only_the_admin_can_set():
    song = type_dto("song", fields=[field_dto("album")])
    types = _types_with(song)

    with pytest.raises(TypeValidationError) as caught:
        _service(types).change(
            "song", _change(song, kinds={"album": FieldKind.CHOICE}), consent=""
        )

    assert caught.value.messages == (
        "A choice field needs settings only the admin has.",
    )
    types.save_all.assert_not_called()


def test_field_use_lists_the_entries_holding_a_value():
    song = type_dto("song", fields=[field_dto("live", FieldKind.BOOL)])
    moose = ref_dto("moose")
    types = _types_with(
        song, values=[(moose, True), (ref_dto("elk"), False), (ref_dto("fox"), None)]
    )
    service = _service(types)

    use = service.field_use("song", "live")

    assert (use.field, use.entries) == (song.fields[0], (moose,))
    for type_key, field_key in (("song", "album"), ("album", "live")):
        with pytest.raises(NotFoundError):
            service.field_use(type_key, field_key)
