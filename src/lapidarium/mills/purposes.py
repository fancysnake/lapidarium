"""The site's types by purpose."""

from typing import TYPE_CHECKING, override

from lapidarium.pacts.purposes import MechanicDTO, TypeUseDTO
from lapidarium.pacts.services import PurposeServiceProtocol
from lapidarium.specs import MECHANIC_NAMES, PURPOSES

if TYPE_CHECKING:
    from lapidarium.pacts.content import EntryTypeRepositoryProtocol


class PurposeService(PurposeServiceProtocol):
    def __init__(self, *, types: EntryTypeRepositoryProtocol) -> None:
        self._types = types

    @override
    def overview(self) -> tuple[MechanicDTO, ...]:
        types = self._types.list_all()
        counts = self._types.entry_counts()
        links = self._types.containment()
        uses = [
            TypeUseDTO(
                entry_type=entry_type,
                entries=counts.get(entry_type.key, 0),
                containers=tuple(t for t in types if (entry_type.key, t.key) in links),
                contents=tuple(t for t in types if (t.key, entry_type.key) in links),
            )
            for entry_type in types
        ]
        return tuple(
            MechanicDTO(
                role=role,
                name=name,
                purposes=tuple(p for p in PURPOSES if p.role == role),
                types=tuple(use for use in uses if use.entry_type.role == role),
            )
            for role, name in MECHANIC_NAMES.items()
        )
