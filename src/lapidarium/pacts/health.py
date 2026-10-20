"""Content health: issues worth a look, and the probe for dead links."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from lapidarium.pacts.content import EntryRefDTO


class HealthIssueDTO(BaseModel):
    """Something about the content worth a look; `entry` when it is about one."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    entry: EntryRefDTO | None


class LinkCheckerProtocol(Protocol):
    def is_alive(self, url: str) -> bool: ...
