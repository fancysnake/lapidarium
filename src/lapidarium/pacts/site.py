"""What every public page carries around its content."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from lapidarium.pacts.content import LinkDTO, ProfileDTO
from lapidarium.pacts.schema import EntryTypeDTO

# Cache alias for rendered public pages; every content commit clears it.
PAGE_CACHE = "pages"


class SiteDTO(BaseModel):
    """What every public page shows around its content."""

    model_config = ConfigDict(frozen=True)

    profile: ProfileDTO | None
    # The profile's name, or the site name when the profile has none.
    owner_name: str
    links: tuple[LinkDTO, ...]
    types: tuple[EntryTypeDTO, ...]
    menu: tuple[EntryTypeDTO, ...]
