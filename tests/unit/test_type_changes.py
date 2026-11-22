from unittest.mock import MagicMock

import pytest

from lapidarium.mills.content import type_to_data
from lapidarium.mills.type_changes import TypeChangeService
from lapidarium.pacts.content import FieldKind, NotFoundError, PartKind
from lapidarium.pacts.purposes import (
    ConsentNeededError,
    TypeEffect,
    TypeSettingsData,
    TypeValidationError,
)
from tests.factories import field_dto, schema_service, type_dto


def _service(types):
    return TypeChangeService(types=types, schema=schema_service())


def _change(entry_type, *, labels=None, added=None, **settings):
    """Return a change that leaves the type as it is, but for the arguments."""
    stored = type_to_data(entry_type)
    return {
        "settings": {
            **{key: stored[key] for key in TypeSettingsData.__annotations__},
            **settings,
        },
        "labels": labels or {field.key: field.label for field in entry_type.fields},
        "added": added,
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
