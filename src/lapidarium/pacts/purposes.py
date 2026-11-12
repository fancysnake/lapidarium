"""Purposes: what an owner wants to show, each on one type role."""

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


class NewTypeData(TypedDict):
    """A type to create from a purpose.

    A blank `key` is derived from `label`. `fields` maps the key of each
    starter field to keep to its label.
    """

    label: str
    label_plural: str
    key: str
    route: str
    colour: str
    fields: dict[str, str]
    allowed_parts: list[PartKind]
    required_parts: list[PartKind]
    in_menu: bool
    has_detail_page: bool
    door_enabled: bool


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
