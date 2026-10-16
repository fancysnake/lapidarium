import datetime as dt

from lapidarium.gates.web.django.ical import Event, calendar

START = dt.datetime(2026, 11, 7, 19, tzinfo=dt.timezone(dt.timedelta(hours=1)))


def _event(**overrides):
    return Event(
        **{
            "uid": "event-online@example.com",
            "stamp": dt.datetime(2026, 10, 14, 12, tzinfo=dt.UTC),
            "start": START,
            "end": None,
            "summary": "Open sessions",
            "description": "One-shots, monthly",
            "location": "",
            "url": "https://example.com/events/online/",
            **overrides,
        }
    )


def test_calendar_with_one_event():
    text = calendar("Mira", [_event()])

    assert text == (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//lapidarium//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "X-WR-CALNAME:Mira\r\n"
        "BEGIN:VEVENT\r\n"
        "UID:event-online@example.com\r\n"
        "DTSTAMP:20261014T120000Z\r\n"
        "DTSTART:20261107T180000Z\r\n"
        "SUMMARY:Open sessions\r\n"
        "DESCRIPTION:One-shots\\, monthly\r\n"
        "URL:https://example.com/events/online/\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )


def test_end_and_location_when_known():
    text = calendar(
        "Mira", [_event(end=START + dt.timedelta(hours=3), location="Toruń")]
    )

    assert "DTEND:20261107T210000Z\r\n" in text
    assert "LOCATION:Toruń\r\n" in text


def test_text_is_escaped():
    text = calendar("Mira", [_event(summary="a;b\\c\nd\r\ne")])

    assert "SUMMARY:a\\;b\\\\c\\nd\\ne\r\n" in text


def test_long_lines_fold_at_75_octets_without_splitting_characters():
    text = calendar("Mira", [_event(description="ł" * 60)])

    lines = text.split("\r\n")
    start = next(i for i, line in enumerate(lines) if line.startswith("DESCRIPTION:"))
    end = next(i for i in range(start + 1, len(lines)) if not lines[i].startswith(" "))
    folded = lines[start:end]
    assert all(len(line.encode()) <= 75 for line in folded)
    assert folded[1].startswith(" ")
    assert "".join([folded[0], *(line[1:] for line in folded[1:])]) == (
        "DESCRIPTION:" + "ł" * 60
    )
