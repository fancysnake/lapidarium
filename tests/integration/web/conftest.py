import datetime as dt
from collections import UserString

import pytest
from django.core.cache import cache
from django.utils import timezone

from lapidarium.inits import Services

NOW = dt.datetime(2026, 10, 14, 12, tzinfo=dt.UTC)


class _StrictUndefined(UserString):
    """`string_if_invalid` that fails the test on an undefined template variable."""

    def __contains__(self, key):
        return key == "%s"

    def __mod__(self, name):
        msg = f"Undefined template variable {name!r}"
        raise AssertionError(msg)


@pytest.fixture(name="browser")
def browser_fixture(*, client, settings, monkeypatch):
    """Return a client reading in English at NOW, failing on undefined variables."""
    templates = [{**t, "OPTIONS": {**t["OPTIONS"]}} for t in settings.TEMPLATES]
    templates[0]["OPTIONS"]["string_if_invalid"] = _StrictUndefined("%s")
    settings.TEMPLATES = templates
    monkeypatch.setattr(timezone, "now", lambda: NOW)
    client.defaults["HTTP_ACCEPT_LANGUAGE"] = "en"
    # Rate limits count in the default cache, which outlives a test.
    cache.clear()
    return client


@pytest.fixture(name="load")
def load_fixture(browser, django_capture_on_commit_callbacks):
    def load(name):
        with django_capture_on_commit_callbacks(execute=True):
            Services().content_import.load_demo(name)
        return browser

    return load


@pytest.fixture(name="site")
def site_fixture(load):
    return load("ttrpg")
