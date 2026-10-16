"""iCalendar (RFC 5545) text for upcoming calendar entries, built by hand."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Iterable

_LINE_OCTETS = 75


class Event(NamedTuple):
    uid: str
    stamp: dt.datetime
    start: dt.datetime
    end: dt.datetime | None
    summary: str
    description: str
    location: str
    url: str


def _text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _utc(value: dt.datetime) -> str:
    return value.astimezone(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def _fold(line: str) -> list[str]:
    """Split `line` into chunks of at most 75 octets, never inside a character."""
    chunks: list[str] = []
    chunk = ""
    for char in line:
        limit = _LINE_OCTETS - (1 if chunks else 0)
        if len((chunk + char).encode()) > limit:
            chunks.append(chunk)
            chunk = ""
        chunk += char
    chunks.append(chunk)
    return [chunks[0], *(f" {c}" for c in chunks[1:])]


def calendar(name: str, events: Iterable[Event]) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//lapidarium//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_text(name)}",
    ]
    for event in events:
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{event.uid}",
                f"DTSTAMP:{_utc(event.stamp)}",
                f"DTSTART:{_utc(event.start)}",
                *([f"DTEND:{_utc(event.end)}"] if event.end else []),
                f"SUMMARY:{_text(event.summary)}",
                f"DESCRIPTION:{_text(event.description)}",
                *([f"LOCATION:{_text(event.location)}"] if event.location else []),
                f"URL:{event.url}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "".join(f"{chunk}\r\n" for line in lines for chunk in _fold(line))
