"""Where uploads go when the settings name a Google Cloud Storage bucket."""

import runpy

from django.utils.module_loading import import_string

from lapidarium.edges import settings


def test_an_upload_to_the_bucket_never_takes_the_name_of_a_stored_file(monkeypatch):
    monkeypatch.setenv("GS_BUCKET_NAME", "uploads")
    default = runpy.run_path(settings.__file__)["STORAGES"]["default"]
    storage = import_string(default["BACKEND"])(**default["OPTIONS"])
    monkeypatch.setattr(storage, "exists", lambda name: name == "assets/cover.png")

    name = storage.get_available_name("assets/cover.png")

    assert name != "assets/cover.png"
    assert name.startswith("assets/cover_")
    assert name.endswith(".png")
