import pytest

from lapidarium.inits import Services


@pytest.fixture(name="media_root")
def media_root_fixture(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    return settings.MEDIA_ROOT


@pytest.fixture(name="demo")
def demo_fixture(media_root, django_capture_on_commit_callbacks):
    """Load the ttrpg demo, its files under this test's own media root."""
    with django_capture_on_commit_callbacks(execute=True):
        Services().content_import.load_demo("ttrpg")
    return media_root
