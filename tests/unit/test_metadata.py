import datetime as dt

import pytest

from lapidarium.mills.metadata import MetadataService
from lapidarium.pacts.content import (
    FieldKind,
    MetadataFitDTO,
    MetadataValidationError,
    UrlKind,
)
from tests.factories import field_dto, type_dto


@pytest.fixture(name="metadata")
def metadata_fixture():
    return MetadataService()


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
def test_validate_metadata_accepts_urls_on_the_kind_host(metadata, case):
    url, kind = case
    entry_type = type_dto(fields=(field_dto("link", FieldKind.URL, url_kind=kind),))

    assert metadata.validate_metadata(entry_type, {"link": url}) == {"link": url}


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
def test_validate_metadata_rejects_urls_off_the_kind_host(metadata, case):
    url, kind, error = case
    entry_type = type_dto(fields=(field_dto("link", FieldKind.URL, url_kind=kind),))

    with pytest.raises(MetadataValidationError) as caught:
        metadata.validate_metadata(entry_type, {"link": url})

    assert caught.value.errors == {"link": error}


def test_validate_metadata_cleans_every_kind(metadata):
    entry_type = type_dto(
        fields=(
            field_dto("system", FieldKind.TEXT),
            field_dto("notes", FieldKind.LONG_TEXT),
            field_dto("recording", FieldKind.URL, url_kind=UrlKind.YOUTUBE),
            field_dto("played", FieldKind.DATE),
            field_dto("players", FieldKind.NUMBER),
            field_dto("hours", FieldKind.NUMBER),
            field_dto("online", FieldKind.BOOL),
            field_dto("format", FieldKind.CHOICE, choices=("one-shot", "campaign")),
            field_dto("inspired_by", FieldKind.RELATION, target_type="session"),
        )
    )

    cleaned = metadata.validate_metadata(
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


def test_validate_metadata_accepts_iso_date_strings(metadata):
    entry_type = type_dto(fields=(field_dto("played", FieldKind.DATE),))

    assert metadata.validate_metadata(entry_type, {"played": "2026-03-14"}) == {
        "played": "2026-03-14"
    }


def test_validate_metadata_reports_everyfield_dto(metadata):
    entry_type = type_dto(
        fields=(
            field_dto("system", FieldKind.TEXT, required=True),
            field_dto("online", FieldKind.BOOL, required=True),
            field_dto("recording", FieldKind.URL, url_kind=UrlKind.YOUTUBE),
            field_dto("played", FieldKind.DATE),
            field_dto("players", FieldKind.NUMBER),
            field_dto("count", FieldKind.NUMBER),
            field_dto("live", FieldKind.BOOL),
            field_dto("format", FieldKind.CHOICE, choices=("one-shot", "campaign")),
        )
    )

    with pytest.raises(MetadataValidationError) as caught:
        metadata.validate_metadata(
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


def test_fit_metadata_fits_stored_values_or_says_why_not(metadata):
    entry_type = type_dto(
        fields=(
            field_dto("system", FieldKind.TEXT),
            field_dto("notes", FieldKind.LONG_TEXT, required=True),
            field_dto("played", FieldKind.DATE),
            field_dto("players", FieldKind.NUMBER),
            field_dto("online", FieldKind.BOOL),
            field_dto("format", FieldKind.CHOICE, choices=("one-shot",)),
            field_dto("inspired_by", FieldKind.RELATION, target_type="session"),
        )
    )

    fits = metadata.fit_metadata(
        entry_type,
        {
            "system": " Mothership ",
            "played": "spring 2024",
            "players": 4.0,
            "online": False,
            "format": "campaign",
            "inspired_by": "moose",
            "dropped": "x",
        },
    )

    assert fits == {
        "system": MetadataFitDTO(value="Mothership"),
        "played": MetadataFitDTO(misfit="Expected a date (YYYY-MM-DD)."),
        "players": MetadataFitDTO(value=4),
        "online": MetadataFitDTO(value=False),
        "format": MetadataFitDTO(misfit="Choose one of: one-shot."),
    }
