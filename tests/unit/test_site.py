from unittest.mock import MagicMock

from lapidarium.mills.site import SiteService
from lapidarium.pacts import LinkDTO, ProfileDTO
from tests.factories import type_dto

PROFILE = ProfileDTO(
    name="Mira", handle="", tagline="", photo=None, bio="", email="mira@example.com"
)
LINK = LinkDTO(platform="itch", url="https://example.itch.io", label="itch.io")


def _service(types=()):
    repos = MagicMock()
    repos.types.list_all.return_value = list(types)
    repos.profile.get.return_value = PROFILE
    repos.profile.list_links.return_value = [LINK]
    repos.schema.derive_tint.return_value = "#f0f0f0"
    service = SiteService(schema=repos.schema, types=repos.types, profile=repos.profile)
    return service, repos


def test_chrome_gives_profile_menu_and_type_colours():
    session = type_dto("session", colour="#6b3fa0", tint="#f3eef9")
    wiki = type_dto("wiki", colour="#0f6b5f", tint="", in_menu=False)
    service, repos = _service(types=[session, wiki])

    site = service.chrome()

    assert site.profile == PROFILE
    assert site.links == (LINK,)
    assert site.types == (session, wiki.model_copy(update={"tint": "#f0f0f0"}))
    assert site.menu == (session,)
    repos.schema.derive_tint.assert_called_once_with("#0f6b5f")
