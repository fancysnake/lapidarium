from unittest.mock import MagicMock

from lapidarium.mills.site import SiteService
from lapidarium.pacts import LinkDTO, ProfileDTO, ThemeDTO
from tests.factories import type_dto

PROFILE = ProfileDTO(
    name="Mira", handle="", tagline="", photo=None, bio="", email="mira@example.com"
)
LINK = LinkDTO(platform="itch", url="https://example.itch.io", label="itch.io")
THEME = ThemeDTO(
    key="base",
    name="Base",
    version="1.0.0",
    engine="0.1",
    fonts=(),
    has_stylesheet=False,
    tokens={},
    dark_tokens={},
    templates=(),
)


def _service(*, types=(), dark=None):
    repos = MagicMock()
    repos.types.list_all.return_value = list(types)
    repos.profile.get.return_value = PROFILE
    repos.profile.list_links.return_value = [LINK]
    repos.schema.derive_tint.return_value = "#f0f0f0"
    repos.theme.dark_background.return_value = dark
    repos.theme.active.return_value = THEME
    service = SiteService(
        schema=repos.schema, types=repos.types, profile=repos.profile, theme=repos.theme
    )
    return service, repos


def test_chrome_gives_profile_menu_and_type_colours():
    session = type_dto("session", colour="#6b3fa0", tint="#f3eef9")
    wiki = type_dto("wiki", colour="#0f6b5f", tint="", in_menu=False)
    service, repos = _service(types=[session, wiki])

    site = service.chrome()

    assert site.profile == PROFILE
    assert site.links == (LINK,)
    assert site.types == (session, wiki.model_copy(update={"tint": "#f0f0f0"}))
    assert site.dark_types == ()
    assert site.menu == (session,)
    assert site.theme == THEME
    repos.schema.derive_tint.assert_called_once_with("#0f6b5f")


def test_chrome_re_derives_tints_for_a_dark_scheme():
    session = type_dto("session", colour="#6b3fa0", tint="#f3eef9")
    service, _ = _service(types=[session], dark="#000000")

    assert service.chrome().dark_types == (
        session.model_copy(update={"tint": "#0d0813"}),
    )
