"""Whether visitors meet the maintenance page, and what it tells them."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, override

from lapidarium.pacts.maintenance import MaintenanceNoticeDTO
from lapidarium.pacts.services import MaintenanceServiceProtocol

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Callable
    from random import Random

    from lapidarium.pacts.maintenance import MaintenanceRepositoryProtocol


class MaintenanceService(MaintenanceServiceProtocol):
    def __init__(
        self,
        *,
        maintenance: MaintenanceRepositoryProtocol,
        clock: Callable[[], dt.datetime],
        rng: Random,
    ) -> None:
        self._maintenance = maintenance
        self._clock = clock
        self._rng = rng

    @override
    def notice(self) -> MaintenanceNoticeDTO | None:
        state = self._maintenance.get()
        now = self._clock()
        if (
            state is None
            or now < state.starts_at
            or (state.ends_at is not None and now >= state.ends_at)
        ):
            return None
        return MaintenanceNoticeDTO(
            ends_at=state.ends_at,
            title=state.title,
            reason=self._rng.choice(state.reasons) if state.reasons else "",
            seconds_left=(
                math.ceil((state.ends_at - now).total_seconds())
                if state.ends_at
                else None
            ),
        )
