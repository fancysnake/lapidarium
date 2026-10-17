from unittest.mock import MagicMock

import pytest

from lapidarium.mills.site import SiteService
from lapidarium.pacts import LinkDTO, ProfileDTO, SiteThemeDTO
from tests.factories import type_dto

PROFILE = ProfileDTO(
    name="Mira", handle="", tagline="", photo=None, bio="", email="mira@example.com"
)
LINK = LinkDTO(platform="itch", url="https://example.itch.io", label="itch.io")
THEME = SiteThemeDTO(key="base", name="Base", version="1.0.0", stylesheets=())


def _service(*, types=(), dark_tint=None, profile=PROFILE):
    repos = MagicMock()
    repos.types.list_all.return_value = list(types)
    repos.profile.get.return_value = profile
    repos.profile.list_links.return_value = [LINK]
    repos.schema.derive_tint.return_value = "#f0f0f0"
    repos.schema.dark_tint.return_value = dark_tint
    repos.theme.active.return_value = THEME
    service = SiteService(
        schema=repos.schema,
        types=repos.types,
        profile=repos.profile,
        theme=repos.theme,
        site_name="Lapidarium",
    )
    return service, repos


def test_chrome_gives_profile_menu_and_type_colours():
    session = type_dto("session", colour="#6b3fa0", tint="#f3eef9")
    wiki = type_dto("wiki", colour="#0f6b5f", tint="", in_menu=False)
    service, repos = _service(types=[session, wiki])

    site = service.chrome()

    assert site.profile == PROFILE
    assert site.owner_name == "Mira"
    assert site.links == (LINK,)
    assert site.types == (session, wiki.model_copy(update={"tint": "#f0f0f0"}))
    assert site.dark_types == ()
    assert site.menu == (session,)
    assert site.theme == THEME
    repos.schema.derive_tint.assert_called_once_with("#0f6b5f")


def test_chrome_re_derives_tints_for_a_dark_scheme():
    session = type_dto("session", colour="#6b3fa0", tint="#f3eef9")
    service, repos = _service(types=[session], dark_tint="#0d0813")

    assert service.chrome().dark_types == (
        session.model_copy(update={"tint": "#0d0813"}),
    )
    repos.schema.dark_tint.assert_called_once_with("#6b3fa0")


@pytest.mark.parametrize("profile", (None, PROFILE.model_copy(update={"name": ""})))
def test_chrome_names_the_site_when_the_profile_names_no_one(profile):
    service, _ = _service(profile=profile)

    assert service.chrome().owner_name == "Lapidarium"
