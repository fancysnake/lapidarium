"""The media files as the content panel lists and changes them."""

from typing import TYPE_CHECKING, override

from lapidarium.mills.catalogue import page_of
from lapidarium.pacts.media import MediaListDTO
from lapidarium.pacts.services import MediaServiceProtocol
from lapidarium.specs import PANEL_PAGE_SIZE

if TYPE_CHECKING:
    from lapidarium.pacts.content import (
        MediaAssetRepositoryProtocol,
        PageCacheProtocol,
        UploadData,
    )


class MediaService(MediaServiceProtocol):
    def __init__(
        self, *, assets: MediaAssetRepositoryProtocol, pages: PageCacheProtocol
    ) -> None:
        self._assets = assets
        self._pages = pages

    @override
    def files(self, *, page: int) -> MediaListDTO:
        assets = self._assets.list_all()
        shown, pages = page_of(assets, page=page, size=PANEL_PAGE_SIZE, label="media")
        return MediaListDTO(
            rows=tuple(shown), page=page, pages=pages, total=len(assets)
        )

    @override
    def upload(self, data: UploadData) -> None:
        self._assets.add(data)

    @override
    def describe(self, path: str, alt: str) -> None:
        self._assets.set_alt(path, alt)
        # Public pages show the alt text, and they are cached.
        self._pages.clear()
