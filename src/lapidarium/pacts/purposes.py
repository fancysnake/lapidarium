"""Purposes: what an owner wants to show, each on one type role."""

from pydantic import BaseModel, ConfigDict

from lapidarium.pacts.content import EntryTypeDTO, FieldKind, TypeRole


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
