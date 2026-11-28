"""What the content panel shows of the media files."""

from pydantic import BaseModel, ConfigDict

from lapidarium.pacts.content import MediaAssetDTO


class MediaListDTO(BaseModel):
    """One page of files, newest first; `total` counts every file."""

    model_config = ConfigDict(frozen=True)

    rows: tuple[MediaAssetDTO, ...]
    page: int
    pages: int
    total: int
