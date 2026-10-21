"""Content health: issues worth a look, and the probe for dead links."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from lapidarium.pacts.content import EntryRefDTO


class HealthProblem(StrEnum):
    EMPTY_CONTAINER = "H001"
    SMALL_DOOR = "H002"
    UNLINKED_PAST = "H003"
    MISSING_COVER = "H004"
    STALE_ONGOING = "H005"
    DEAD_LINK = "H006"


class HealthIssueDTO(BaseModel):
    """Something about the content worth a look; `entry` when it is about one."""

    model_config = ConfigDict(frozen=True)

    code: HealthProblem
    message: str
    entry: EntryRefDTO | None

    @property
    def line(self) -> str:
        where = f"{self.entry.type_key}/{self.entry.slug}: " if self.entry else ""
        return f"{self.code} {where}{self.message}"


class LinkCheckerProtocol(Protocol):
    def is_alive(self, url: str) -> bool: ...
