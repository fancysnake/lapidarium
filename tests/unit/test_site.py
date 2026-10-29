from unittest.mock import MagicMock

import pytest

from lapidarium.mills.site import SiteService
from lapidarium.pacts.site import FriendDTO, LinkDTO, TypeColourDTO
from tests.factories import profile_dto, type_dto

PROFILE = profile_dto()
LINK = LinkDTO(platform="itch", url="https://example.itch.io", label="itch.io")
FRIEND = FriendDTO(name="Ada", url="https://ada.example.org", button=None)


def _service(*, types=(), profile=PROFILE, dark_colours=None):
    repos = MagicMock()
    repos.types.list_all.return_value = list(types)
    repos.profile.get.return_value = profile
    repos.profile.list_links.return_value = [LINK]
    repos.profile.list_friends.return_value = [FRIEND]
    schema = MagicMock()
    schema.derive_dark_colour.side_effect = (dark_colours or {}).get
    return SiteService(
        types=repos.types, profile=repos.profile, schema=schema, site_name="Lapidarium"
    )


def test_chrome_gives_profile_menu_and_types():
    session = type_dto("session", colour="#6b3fa0", tint="#f3eef9")
    wiki = type_dto("wiki", colour="#0f6b5f", tint="", in_menu=False)

    site = _service(types=[session, wiki]).chrome()

    assert site.profile == PROFILE
    assert site.owner_name == "Mira"
    assert site.links == (LINK,)
    assert site.types == (session, wiki)
    assert site.menu == (session,)
    assert site.dark_colours == ()


def test_chrome_gives_the_dark_colours_that_differ():
    session = type_dto("session", colour="#6b3fa0", tint="")
    wiki = type_dto("wiki", colour="#c9a0ff", tint="")
    darks = {"#6b3fa0": "#9779bc", "#c9a0ff": "#c9a0ff"}

    site = _service(types=[session, wiki], dark_colours=darks).chrome()

    assert site.dark_colours == (TypeColourDTO(key="session", colour="#9779bc"),)


@pytest.mark.parametrize("profile", (None, PROFILE.model_copy(update={"name": ""})))
def test_chrome_names_the_site_when_the_profile_names_no_one(profile):
    assert _service(profile=profile).chrome().owner_name == "Lapidarium"


def test_friends_are_those_the_profile_keeps():
    assert _service().friends() == (FRIEND,)
