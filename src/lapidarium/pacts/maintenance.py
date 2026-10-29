"""The window in which the whole site is hidden from visitors."""

from __future__ import annotations

import datetime as dt
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class MaintenanceDTO(BaseModel):
    """The site-wide switch that hides the site from visitors."""

    model_config = ConfigDict(frozen=True)

    starts_at: dt.datetime
    ends_at: dt.datetime | None
    title: str
    reasons: tuple[str, ...]


class MaintenanceNoticeDTO(BaseModel):
    """What a visitor sees while the site is in maintenance."""

    model_config = ConfigDict(frozen=True)

    ends_at: dt.datetime | None
    title: str
    reason: str
    # Whole seconds until `ends_at`, rounded up; `None` without an end.
    seconds_left: int | None


class MaintenanceRepositoryProtocol(Protocol):
    def get(self) -> MaintenanceDTO | None: ...
