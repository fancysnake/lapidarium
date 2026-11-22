"""Purposes: what an owner wants to show, each on one type role."""

from enum import StrEnum
from typing import TYPE_CHECKING, TypedDict

from pydantic import BaseModel, ConfigDict

from lapidarium.pacts.content import EntryTypeDTO, FieldKind, PartKind, TypeRole

if TYPE_CHECKING:
    from collections.abc import Sequence


class TypeValidationError(Exception):
    """A type that breaks the schema rules, one message per broken rule."""

    def __init__(self, messages: Sequence[str]) -> None:
        super().__init__("; ".join(messages))
        self.messages = tuple(messages)


class TypeEffect(StrEnum):
    """What a change to a type does to entries it already has."""

    MOVED = "moved"
    PAGE_LOST = "page_lost"
    PAGE_GAINED = "page_gained"
    PART_REFUSED = "part_refused"
    PART_MISSING = "part_missing"


class TypeSettingsData(TypedDict):
    """Settings both type forms of the panel hold."""

    label: str
    label_plural: str
    route: str
    colour: str
    allowed_parts: list[PartKind]
    required_parts: list[PartKind]
    in_menu: bool
    has_detail_page: bool
    door_enabled: bool


class NewTypeData(TypedDict):
    """A type to create from a purpose.

    A blank `key` is derived from the label in `settings`. `labels` maps the key
    of each starter field to its label; a field left out of it is dropped, and
    the form leaves out the ones with a blank label.
    """

    settings: TypeSettingsData
    key: str
    labels: dict[str, str]


class NewFieldData(TypedDict):
    """A field to add to a type; its key is derived from `label`."""

    label: str
    kind: FieldKind


class TypeChangeData(TypedDict):
    """New settings for a type; `labels` maps the key of each field to its label."""

    settings: TypeSettingsData
    labels: dict[str, str]
    added: NewFieldData | None


class StarterFieldDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    label: str
    kind: FieldKind = FieldKind.TEXT


class PurposeDTO(BaseModel):
    """`label`, `label_plural`, `route` and `fields` suggest the type to create."""

    model_config = ConfigDict(frozen=True)

    key: str
    name: str
    description: str
    role: TypeRole
    label: str
    label_plural: str
    route: str
    fields: tuple[StarterFieldDTO, ...] = ()


class TypeUseDTO(BaseModel):
    """A type with its entry count and the types its entries belong to and hold."""

    model_config = ConfigDict(frozen=True)

    entry_type: EntryTypeDTO
    entries: int
    containers: tuple[EntryTypeDTO, ...]
    contents: tuple[EntryTypeDTO, ...]


class MechanicDTO(BaseModel):
    """A type role under the owner's name for it, its purposes and its types."""

    model_config = ConfigDict(frozen=True)

    role: TypeRole
    name: str
    purposes: tuple[PurposeDTO, ...]
    types: tuple[TypeUseDTO, ...]


class TypeEffectDTO(BaseModel):
    """An effect on `entries` entries; `part` is set for the two part effects."""

    model_config = ConfigDict(frozen=True)

    kind: TypeEffect
    entries: int
    part: PartKind | None = None


class TypeChangeDTO(BaseModel):
    """A type as a change leaves it, and what the change does to its entries."""

    model_config = ConfigDict(frozen=True)

    entry_type: EntryTypeDTO
    effects: tuple[TypeEffectDTO, ...]

    @property
    def consent(self) -> str:
        """What the owner sends back to agree to exactly these effects."""
        return ",".join(f"{e.kind}:{e.part or ''}:{e.entries}" for e in self.effects)


class ConsentNeededError(Exception):
    """A change sent without consent to exactly the effects `change` has."""

    def __init__(self, change: TypeChangeDTO) -> None:
        super().__init__(change.consent)
        self.change = change
