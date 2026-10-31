"""No type's route can take a first path segment the URLconf serves itself."""

from django.urls import get_resolver

from lapidarium.inits import Services


def _literal_first_segments():
    for pattern in get_resolver().url_patterns:
        segment = str(pattern.pattern).split("/", maxsplit=1)[0]
        # `<slug:…>` is a type's route; a slug cannot hold the dot of the feeds.
        if segment and not segment.startswith("<") and "." not in segment:
            yield segment


def test_every_literal_first_segment_is_refused_as_a_route():
    schema = Services().schema
    segments = set(_literal_first_segments())

    assert "about" in segments
    assert {s for s in segments if not schema.check_route(s)} == set()
