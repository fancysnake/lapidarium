"""Entry metadata against its type's fields: cleaning input, fitting stored values."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, override

from lapidarium.mills.schema import url_host
from lapidarium.pacts.content import (
    FieldKind,
    MetadataFitDTO,
    MetadataValidationError,
    UrlKind,
)
from lapidarium.pacts.services import MetadataServiceProtocol
from lapidarium.specs import GITHUB_HOSTS, ITCH_HOST, YOUTUBE_HOSTS

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from lapidarium.pacts.content import (
        EntryTypeDTO,
        FieldDefinitionDTO,
        Metadata,
        MetadataInput,
        MetadataValue,
    )


def _url_error(url: str, url_kind: UrlKind) -> str | None:
    if (host := url_host(url)) is None:
        return "Enter a full http(s) address."
    match url_kind:
        case UrlKind.YOUTUBE if host not in YOUTUBE_HOSTS:
            return "Enter a YouTube address."
        case UrlKind.ITCH if host != ITCH_HOST and not host.endswith(f".{ITCH_HOST}"):
            return "Enter an itch.io address."
        case UrlKind.GITHUB if host not in GITHUB_HOSTS:
            return "Enter a GitHub address."
        case _:
            return None


type _Given = str | float | dt.date


def _clean_text(value: _Given, _field: FieldDefinitionDTO) -> str:
    return str(value).strip()


def _clean_url(value: _Given, field: FieldDefinitionDTO) -> str:
    url = str(value).strip()
    if error := _url_error(url, field.url_kind):
        raise ValueError(error)
    return url


def _clean_choice(value: _Given, field: FieldDefinitionDTO) -> str:
    if str(value) not in field.choices:
        msg = f"Choose one of: {', '.join(field.choices)}."
        raise ValueError(msg)
    return str(value)


def _clean_bool(value: _Given, _field: FieldDefinitionDTO) -> bool:
    if not isinstance(value, bool):
        msg = "Expected yes or no."
        raise TypeError(msg)
    return value


def _clean_number(value: _Given, _field: FieldDefinitionDTO) -> int | float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = "Expected a number."
        raise TypeError(msg)
    return int(value) if float(value).is_integer() else value


def _clean_date(value: _Given, _field: FieldDefinitionDTO) -> str:
    if isinstance(value, dt.date):
        return value.isoformat()
    try:
        return dt.date.fromisoformat(str(value)).isoformat()
    except ValueError:
        msg = "Expected a date (YYYY-MM-DD)."
        raise ValueError(msg) from None


# Every kind but `relation`, whose values are links rather than metadata.
_CLEANERS: Mapping[FieldKind, Callable[[_Given, FieldDefinitionDTO], MetadataValue]] = {
    FieldKind.TEXT: _clean_text,
    FieldKind.LONG_TEXT: _clean_text,
    FieldKind.URL: _clean_url,
    FieldKind.DATE: _clean_date,
    FieldKind.NUMBER: _clean_number,
    FieldKind.BOOL: _clean_bool,
    FieldKind.CHOICE: _clean_choice,
}


def validate_metadata(
    entry_type: EntryTypeDTO, values: Mapping[str, MetadataInput]
) -> Metadata:
    """Return cleaned metadata, or raise `MetadataValidationError`."""
    fields = {f.key: f for f in entry_type.fields if f.kind in _CLEANERS}
    errors = {key: "Not a field of this type." for key in values if key not in fields}
    cleaned: Metadata = {}
    for key, field in fields.items():
        value = values.get(key)
        if value is None or not str(value):
            if field.required and field.kind.can_be_missing:
                errors[key] = "This field is required."
            continue
        try:
            cleaned[key] = _CLEANERS[field.kind](value, field)
        except (TypeError, ValueError) as exc:
            errors[key] = str(exc)
    if errors:
        raise MetadataValidationError(errors)
    return cleaned


class MetadataService(MetadataServiceProtocol):
    @override
    def validate_metadata(
        self, entry_type: EntryTypeDTO, values: Mapping[str, MetadataInput]
    ) -> Metadata:
        return validate_metadata(entry_type, values)

    @override
    def fit_metadata(
        self, entry_type: EntryTypeDTO, stored: Mapping[str, MetadataValue]
    ) -> dict[str, MetadataFitDTO]:
        fits: dict[str, MetadataFitDTO] = {}
        for field in entry_type.fields:
            value = stored.get(field.key)
            if field.kind not in _CLEANERS or value is None or not str(value):
                continue
            try:
                fits[field.key] = MetadataFitDTO(
                    value=_CLEANERS[field.kind](value, field)
                )
            except (TypeError, ValueError) as exc:
                fits[field.key] = MetadataFitDTO(misfit=str(exc))
        return fits
