"""What frames every public page, and what replaces them in maintenance."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, override

from lapidarium.pacts.services import SiteServiceProtocol
from lapidarium.pacts.site import MaintenanceNoticeDTO, SiteDTO, TypeColourDTO

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Callable
    from random import Random

    from lapidarium.pacts.content import EntryTypeRepositoryProtocol
    from lapidarium.pacts.services import SchemaServiceProtocol
    from lapidarium.pacts.site import (
        FriendDTO,
        MaintenanceRepositoryProtocol,
        ProfileDTO,
        ProfileRepositoryProtocol,
    )


class SiteService(SiteServiceProtocol):
    def __init__(
        self,
        *,
        types: EntryTypeRepositoryProtocol,
        profile: ProfileRepositoryProtocol,
        maintenance: MaintenanceRepositoryProtocol,
        schema: SchemaServiceProtocol,
        site_name: str,
        clock: Callable[[], dt.datetime],
        rng: Random,
    ) -> None:
        self._types = types
        self._profile = profile
        self._maintenance = maintenance
        self._schema = schema
        self._site_name = site_name
        self._clock = clock
        self._rng = rng

    @override
    def chrome(self) -> SiteDTO:
        types = tuple(self._types.list_all())
        profile = self._profile.get()
        return SiteDTO(
            profile=profile,
            owner_name=self._owner_name(profile),
            links=tuple(self._profile.list_links()),
            types=types,
            menu=tuple(t for t in types if t.in_menu),
            dark_colours=tuple(
                TypeColourDTO(key=t.key, colour=dark)
                for t in types
                if (dark := self._schema.derive_dark_colour(t.colour))
                not in {None, t.colour}
            ),
        )

    @override
    def friends(self) -> tuple[FriendDTO, ...]:
        return tuple(self._profile.list_friends())

    @override
    def maintenance(self) -> MaintenanceNoticeDTO | None:
        state = self._maintenance.get()
        now = self._clock()
        if (
            state is None
            or not state.enabled
            or now < state.starts_at
            or (state.ends_at is not None and now >= state.ends_at)
        ):
            return None
        profile = self._profile.get()
        return MaintenanceNoticeDTO(
            profile=profile,
            owner_name=self._owner_name(profile),
            starts_at=state.starts_at,
            ends_at=state.ends_at,
            reason=self._rng.choice(state.reasons) if state.reasons else "",
            retry_after=(
                math.ceil((state.ends_at - now).total_seconds())
                if state.ends_at
                else None
            ),
        )

    def _owner_name(self, profile: ProfileDTO | None) -> str:
        return (profile.name if profile else "") or self._site_name
