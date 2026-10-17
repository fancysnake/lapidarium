from unittest.mock import MagicMock

import pytest

from lapidarium.mills.site import SiteService
from lapidarium.pacts import LinkDTO, ProfileDTO
from tests.factories import type_dto

PROFILE = ProfileDTO(
    name="Mira", handle="", tagline="", photo=None, bio="", email="mira@example.com"
)
LINK = LinkDTO(platform="itch", url="https://example.itch.io", label="itch.io")


def _service(*, types=(), profile=PROFILE):
    repos = MagicMock()
    repos.types.list_all.return_value = list(types)
    repos.profile.get.return_value = profile
    repos.profile.list_links.return_value = [LINK]
    return SiteService(types=repos.types, profile=repos.profile, site_name="Lapidarium")


def test_chrome_gives_profile_menu_and_types():
    session = type_dto("session", colour="#6b3fa0", tint="#f3eef9")
    wiki = type_dto("wiki", colour="#0f6b5f", tint="", in_menu=False)

    site = _service(types=[session, wiki]).chrome()

    assert site.profile == PROFILE
    assert site.owner_name == "Mira"
    assert site.links == (LINK,)
    assert site.types == (session, wiki)
    assert site.menu == (session,)


@pytest.mark.parametrize("profile", (None, PROFILE.model_copy(update={"name": ""})))
def test_chrome_names_the_site_when_the_profile_names_no_one(profile):
    assert _service(profile=profile).chrome().owner_name == "Lapidarium"
