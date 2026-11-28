from unittest.mock import MagicMock

import pytest

from lapidarium.mills.media import MediaService
from lapidarium.pacts.content import MediaAssetDTO, NotFoundError
from lapidarium.specs import PANEL_PAGE_SIZE


def _asset(path, alt=""):
    return MediaAssetDTO(path=path, url=f"/media/{path}", alt=alt)


def _service(assets=(), pages=None):
    repo = MagicMock()
    repo.list_all.return_value = list(assets)
    return MediaService(assets=repo, pages=pages or MagicMock()), repo


def test_files_come_a_page_at_a_time():
    assets = [_asset(f"assets/{index}.png") for index in range(PANEL_PAGE_SIZE + 1)]

    files = _service(assets)[0].files(page=2)

    assert files.rows == tuple(assets[PANEL_PAGE_SIZE:])
    assert (files.page, files.pages, files.total) == (2, 2, len(assets))


def test_files_have_no_page_past_the_last():
    with pytest.raises(NotFoundError):
        _service()[0].files(page=2)


def test_upload_stores_the_file():
    service, repo = _service()
    data = {"name": "cover.png", "content": MagicMock(), "alt": "A moose"}

    service.upload(data)

    repo.add.assert_called_once_with(data)


def test_describe_changes_the_alt_text_and_clears_the_cached_pages():
    pages = MagicMock()
    service, repo = _service(pages=pages)

    service.describe("assets/cover.png", "A moose")

    repo.set_alt.assert_called_once_with("assets/cover.png", "A moose")
    pages.clear.assert_called_once_with()


def test_describe_keeps_the_cached_pages_when_no_file_has_the_path():
    pages = MagicMock()
    service, repo = _service(pages=pages)
    repo.set_alt.side_effect = NotFoundError("assets/gone.png")

    with pytest.raises(NotFoundError):
        service.describe("assets/gone.png", "A moose")

    pages.clear.assert_not_called()
