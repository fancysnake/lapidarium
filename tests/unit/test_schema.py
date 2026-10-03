import datetime as dt

import pytest

from lapidarium.mills import SchemaService, contrast_ratio, mix
from lapidarium.pacts import (
    FIELD_DEFAULTS,
    EntryTypeDTO,
    FieldDefinitionDTO,
    FieldKind,
    MetadataValidationError,
    PartKind,
    RelationEndDTO,
    TypeRole,
    UrlKind,
)
from tests.factories import builtins, part_data

WHITE = "#ffffff"
BLACK = "#000000"


def _field(key, kind, **overrides):
    defaults = {"label": key.title(), **FIELD_DEFAULTS}
    return FieldDefinitionDTO(key=key, kind=kind, **(defaults | overrides))


def _type(*fields, allowed=(PartKind.TEXT,), required=()):
    return EntryTypeDTO(
        key="session",
        label="Session",
        label_plural="Sessions",
        route="sessions",
        colour=BLACK,
        tint="",
        icon="",
        order=0,
        in_menu=True,
        role=TypeRole.THING,
        layout="article",
        allowed_parts=allowed,
        required_parts=required,
        door_enabled=False,
        door_label="",
        door_pick="latest",
        door_min_entries=1,
        list_filters=(),
        has_detail_page=True,
        fields=fields,
    )


@pytest.fixture(name="schema")
def schema_fixture():
    return SchemaService(background=WHITE)


def test_contrast_ratio_spans_one_to_twenty_one():
    assert contrast_ratio(BLACK, WHITE) == pytest.approx(21)
    assert contrast_ratio("#777777", "#777777") == pytest.approx(1)


def test_mix_lays_a_share_of_one_colour_over_another():
    assert mix(BLACK, WHITE, share=0.5) == "#808080"


@pytest.mark.parametrize(
    "case",
    (
        ("https://www.youtube.com/watch?v=x", UrlKind.YOUTUBE),
        ("https://youtu.be/x", UrlKind.YOUTUBE),
        ("https://itch.io/games", UrlKind.ITCH),
        ("https://someone.itch.io/game", UrlKind.ITCH),
        ("https://github.com/x/y", UrlKind.GITHUB),
        ("https://example.com", UrlKind.ANY_HOST),
    ),
)
def test_validate_metadata_accepts_urls_on_the_kind_host(schema, case):
    url, kind = case
    entry_type = _type(_field("link", FieldKind.URL, url_kind=kind))

    assert schema.validate_metadata(entry_type, {"link": url}) == {"link": url}


@pytest.mark.parametrize(
    "case",
    (
        ("https://vimeo.com/1", UrlKind.YOUTUBE, "Enter a YouTube address."),
        ("https://notitch.io/game", UrlKind.ITCH, "Enter an itch.io address."),
        ("https://gitlab.com/x/y", UrlKind.GITHUB, "Enter a GitHub address."),
        ("ftp://example.com", UrlKind.ANY_HOST, "Enter a full http(s) address."),
        ("example.com", UrlKind.ANY_HOST, "Enter a full http(s) address."),
    ),
)
def test_validate_metadata_rejects_urls_off_the_kind_host(schema, case):
    url, kind, error = case
    entry_type = _type(_field("link", FieldKind.URL, url_kind=kind))

    with pytest.raises(MetadataValidationError) as caught:
        schema.validate_metadata(entry_type, {"link": url})

    assert caught.value.errors == {"link": error}


def test_validate_metadata_cleans_every_kind(schema):
    entry_type = _type(
        _field("system", FieldKind.TEXT),
        _field("notes", FieldKind.LONG_TEXT),
        _field("recording", FieldKind.URL, url_kind=UrlKind.YOUTUBE),
        _field("played", FieldKind.DATE),
        _field("players", FieldKind.NUMBER),
        _field("hours", FieldKind.NUMBER),
        _field("online", FieldKind.BOOL),
        _field("format", FieldKind.CHOICE, choices=("one-shot", "campaign")),
        _field("inspired_by", FieldKind.RELATION, target_type="session"),
    )

    cleaned = schema.validate_metadata(
        entry_type,
        {
            "system": " Mothership ",
            "notes": "",
            "recording": "https://youtu.be/x",
            "played": dt.date(2026, 3, 14),
            "players": 4.0,
            "hours": 2.5,
            "online": False,
            "format": "one-shot",
        },
    )

    assert cleaned == {
        "system": "Mothership",
        "recording": "https://youtu.be/x",
        "played": "2026-03-14",
        "players": 4,
        "hours": 2.5,
        "online": False,
        "format": "one-shot",
    }


def test_validate_metadata_accepts_iso_date_strings(schema):
    entry_type = _type(_field("played", FieldKind.DATE))

    assert schema.validate_metadata(entry_type, {"played": "2026-03-14"}) == {
        "played": "2026-03-14"
    }


def test_validate_metadata_reports_every_field(schema):
    entry_type = _type(
        _field("system", FieldKind.TEXT, required=True),
        _field("online", FieldKind.BOOL, required=True),
        _field("recording", FieldKind.URL, url_kind=UrlKind.YOUTUBE),
        _field("played", FieldKind.DATE),
        _field("players", FieldKind.NUMBER),
        _field("count", FieldKind.NUMBER),
        _field("live", FieldKind.BOOL),
        _field("format", FieldKind.CHOICE, choices=("one-shot", "campaign")),
    )

    with pytest.raises(MetadataValidationError) as caught:
        schema.validate_metadata(
            entry_type,
            {
                "recording": "https://vimeo.com/1",
                "played": "March",
                "players": "four",
                "count": True,
                "live": "yes",
                "format": "sandbox",
                "colour": "red",
            },
        )

    assert caught.value.errors == {
        "colour": "Not a field of this type.",
        "system": "This field is required.",
        "recording": "Enter a YouTube address.",
        "played": "Expected a date (YYYY-MM-DD).",
        "players": "Expected a number.",
        "count": "Expected a number.",
        "live": "Expected yes or no.",
        "format": "Choose one of: one-shot, campaign.",
    }
    assert "system: This field is required." in str(caught.value)


@pytest.mark.parametrize(
    "case",
    (
        (TypeRole.THING, builtins(date=dt.date(2026, 1, 1)), {}),
        (
            TypeRole.THING,
            builtins(location="Poznań", is_online=True),
            {
                "location": "Not used by the thing role.",
                "is_online": "Not used by the thing role.",
            },
        ),
        (
            TypeRole.CALENDAR,
            builtins(location="Poznań"),
            {"start_at": "This field is required."},
        ),
        (
            TypeRole.CALENDAR,
            builtins(
                start_at=dt.datetime(2026, 6, 2, tzinfo=dt.UTC),
                end_at=dt.datetime(2026, 6, 1, tzinfo=dt.UTC),
            ),
            {"end_at": "Ends before it starts."},
        ),
        (
            TypeRole.CONTAINER_OUTCOME,
            builtins(date=dt.date(2026, 1, 1)),
            {
                "date": "Not used by the container_outcome role.",
                "outcome": "This field is required.",
            },
        ),
        (
            TypeRole.CONTAINER_TIMESPAN,
            builtins(start_at=dt.datetime(2021, 1, 1, tzinfo=dt.UTC)),
            {},
        ),
    ),
)
def test_check_builtins(schema, case):
    role, values, errors = case

    assert schema.check_builtins(role, values) == errors


@pytest.mark.parametrize(
    "case",
    (
        (part_data(PartKind.TEXT, text="AAR"), None, []),
        (part_data(PartKind.TEXT, text="  "), None, ["A text part needs text."]),
        (part_data(PartKind.VIDEO), None, ["A video part needs a URL."]),
        (part_data(PartKind.LINK, url="https://a.example"), None, []),
        (part_data(PartKind.AUDIO), None, ["An audio part needs a URL or a file."]),
        (part_data(PartKind.AUDIO, asset="assets/a.ogg"), "", []),
        (part_data(PartKind.FILE), None, ["The file part needs an uploaded file."]),
        (
            part_data(PartKind.IMAGE, asset="assets/a.png"),
            "",
            ["An image part needs alt text on its asset."],
        ),
        (part_data(PartKind.IMAGE, asset="assets/a.png"), "A moose", []),
        (
            part_data(PartKind.LINK, url="itch.io"),
            None,
            ["Enter a full http(s) address."],
        ),
    ),
)
def test_check_part(schema, case):
    part, alt, errors = case

    assert schema.check_part(part, alt) == errors


def test_check_part_kinds(schema):
    entry_type = _type(
        allowed=(PartKind.TEXT, PartKind.VIDEO), required=(PartKind.TEXT,)
    )

    assert schema.check_part_kinds(entry_type, [PartKind.TEXT]) == []
    assert schema.check_part_kinds(
        entry_type, [PartKind.IMAGE, PartKind.IMAGE, PartKind.VIDEO]
    ) == [
        "Session does not allow image parts.",
        "Session needs at least one text part.",
    ]


SESSION = _type(_field("inspired_by", FieldKind.RELATION, target_type="session"))
PROJECT = _type().model_copy(
    update={"key": "project", "label": "Project", "role": TypeRole.CONTAINER_OUTCOME}
)


def _end(entry_type, status="published"):
    return RelationEndDTO(entry_type=entry_type, status=status)


@pytest.mark.parametrize(
    "case",
    (
        ("part_of", _end(PROJECT), []),
        ("part_of", _end(SESSION), ["Only containers can hold entries."]),
        ("related", _end(SESSION), []),
        ("inspired_by", _end(SESSION), []),
        ("inspired_by", _end(PROJECT), ["Inspired_By cannot link to a Project."]),
        ("sequel_of", _end(SESSION), ["Unknown relation role 'sequel_of'."]),
        (
            "related",
            _end(SESSION, "draft"),
            ["A published entry cannot link to a draft."],
        ),
    ),
)
def test_check_relation(schema, case):
    role, target, errors = case

    assert schema.check_relation(role, source=_end(SESSION), target=target) == errors


def test_check_relation_lets_drafts_link_anywhere(schema):
    source, target = _end(SESSION, "draft"), _end(SESSION, "draft")

    assert schema.check_relation("related", source=source, target=target) == []


def test_check_loop_walks_the_part_of_chain(schema):
    part_of = {"arc": ["saga"], "saga": ["campaign"]}

    def containers(keys):
        return [c for key in keys for c in part_of.get(key, ())]

    loop = ["That makes a loop of containers."]
    assert (
        schema.check_loop(
            "part_of", entry="campaign", target="arc", containers=containers
        )
        == loop
    )
    assert (
        schema.check_loop("part_of", entry="arc", target="arc", containers=containers)
        == loop
    )
    assert (
        schema.check_loop(
            "part_of", entry="arc", target="campaign", containers=containers
        )
        == []
    )
    assert (
        schema.check_loop(
            "related", entry="campaign", target="arc", containers=containers
        )
        == []
    )


def test_check_relation_roles_wants_required_fields_linked(schema):
    entry_type = _type(
        _field("inspired_by", FieldKind.RELATION, required=True),
        _field("sequel_of", FieldKind.RELATION, required=True),
        _field("system", FieldKind.TEXT, required=True),
    )

    assert schema.check_relation_roles(entry_type, ["part_of"]) == [
        "Link at least one entry as: Inspired_By, Sequel_Of."
    ]
    assert schema.check_relation_roles(entry_type, ["inspired_by", "sequel_of"]) == []


def test_derive_tint_is_a_light_mix_with_the_background(schema):
    assert schema.derive_tint(BLACK) == "#e0e0e0"


def test_check_colours(schema):
    assert schema.check_colours("#6b3fa0", schema.derive_tint("#6b3fa0")) == []
    assert schema.check_colours("#999999", "#999999") == [
        "Contrast with the page background is 2.85:1, needs 4.5:1.",
        "Contrast with the tint is 1.00:1, needs 4.5:1.",
    ]
