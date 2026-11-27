"""What the content panel shows of the entries, drafts among them."""

from pydantic import BaseModel, ConfigDict

from lapidarium.pacts.content import EntryDTO, EntryRefDTO, EntryStatus, EntryTypeDTO


class EntryRowDTO(BaseModel):
    """An entry with its type and the containers it is part of."""

    model_config = ConfigDict(frozen=True)

    entry: EntryDTO
    entry_type: EntryTypeDTO
    containers: tuple[EntryRefDTO, ...]


class TypeCountDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    entry_type: EntryTypeDTO
    entries: int


class DeskDTO(BaseModel):
    """Drafts and the latest published entries, both newest change first."""

    model_config = ConfigDict(frozen=True)

    drafts: tuple[EntryRowDTO, ...]
    published: tuple[EntryRowDTO, ...]
    total: int


class EntryListDTO(BaseModel):
    """One page of entries, newest change first.

    `entry_type`, `status` and `query` are the filters in force. `total`,
    `published` and `drafts` count the entries of the type that match the
    query, whatever the status filter.
    """

    model_config = ConfigDict(frozen=True)

    rows: tuple[EntryRowDTO, ...]
    types: tuple[TypeCountDTO, ...]
    entry_type: EntryTypeDTO | None
    status: EntryStatus | None
    query: str
    page: int
    pages: int
    total: int
    published: int
    drafts: int
