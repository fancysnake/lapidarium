import datetime as dt
from unittest.mock import MagicMock

from lapidarium.mills.site import SiteService
from lapidarium.pacts import LinkDTO, ProfileDTO, ThemeDTO, TypeRole
from tests.factories import entry_dto, type_dto

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


def _service(*, types=(), entries=(), dark=None):
    repos = MagicMock()
    repos.types.list_all.return_value = list(types)
    repos.entries.list_published.return_value = list(entries)
    repos.profile.get.return_value = PROFILE
    repos.profile.list_links.return_value = [LINK]
    repos.schema.derive_tint.return_value = "#f0f0f0"
    repos.theme.dark_background.return_value = dark
    repos.theme.active.return_value = THEME
    service = SiteService(
        schema=repos.schema,
        types=repos.types,
        entries=repos.entries,
        profile=repos.profile,
        theme=repos.theme,
    )
    return service, repos


def test_chrome_gives_profile_menu_and_type_colours():
    session = type_dto("session", colour="#6b3fa0", tint="#f3eef9")
    wiki = type_dto("wiki", colour="#0f6b5f", tint="", in_menu=False)
    service, repos = _service(types=[session, wiki])

    site = service.chrome()

    assert site.profile == PROFILE
    assert site.links == (LINK,)
    assert site.types == (session, wiki)
    assert site.menu == (session,)
    assert site.theme == THEME
    assert site.type_css == (
        '[data-type="session"] { --type-color: #6b3fa0; --type-tint: #f3eef9; }\n'
        '[data-type="wiki"] { --type-color: #0f6b5f; --type-tint: #f0f0f0; }'
    )
    repos.schema.derive_tint.assert_called_once_with("#0f6b5f")


def test_about_lists_containers_newest_first():
    project = type_dto("project", role=TypeRole.CONTAINER_OUTCOME)
    initiative = type_dto("initiative", role=TypeRole.CONTAINER_TIMESPAN)
    start = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
    entries = [
        entry_dto("old", "initiative", start_at=start - dt.timedelta(days=900)),
        entry_dto("new", "project", start_at=start),
        entry_dto("session"),
    ]
    service, _ = _service(types=[type_dto(), project, initiative], entries=entries)

    about = service.about()

    assert about.profile == PROFILE
    assert about.links == (LINK,)
    assert [c.entry.slug for c in about.timeline] == ["new", "old"]


def test_chrome_re_derives_tints_for_a_dark_scheme():
    session = type_dto("session", colour="#6b3fa0", tint="#f3eef9")
    service, _ = _service(types=[session], dark="#000000")

    assert service.chrome().type_css.endswith(
        "@media (prefers-color-scheme: dark) {\n"
        '  [data-type="session"] { --type-tint: #0d0813; }\n'
        "}"
    )
