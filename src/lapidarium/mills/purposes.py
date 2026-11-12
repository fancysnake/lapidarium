"""The site's types by purpose, and new types from a purpose."""

import re
from typing import TYPE_CHECKING, override

from lapidarium.mills.content import type_to_data
from lapidarium.mills.schema import type_errors
from lapidarium.pacts.content import (
    FIELD_DEFAULTS,
    TYPE_DEFAULTS,
    EntryTypeDTO,
    FieldDefinitionDTO,
    NotFoundError,
    SettingDefault,
)
from lapidarium.pacts.purposes import (
    MechanicDTO,
    NewTypeData,
    PurposeDTO,
    TypeUseDTO,
    TypeValidationError,
)
from lapidarium.pacts.services import PurposeServiceProtocol, SchemaServiceProtocol
from lapidarium.specs import MECHANIC_NAMES, PURPOSES

if TYPE_CHECKING:
    from lapidarium.pacts.content import EntryTypeRepositoryProtocol


def _key(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


class PurposeService(PurposeServiceProtocol):
    def __init__(
        self, *, types: EntryTypeRepositoryProtocol, schema: SchemaServiceProtocol
    ) -> None:
        self._types = types
        self._schema = schema

    @override
    def overview(self) -> tuple[MechanicDTO, ...]:
        types = self._types.list_all()
        counts = self._types.entry_counts()
        links = self._types.containment()
        uses = [
            TypeUseDTO(
                entry_type=entry_type,
                entries=counts[entry_type.key],
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

    @override
    def purpose(self, key: str) -> PurposeDTO:
        if (found := next((p for p in PURPOSES if p.key == key), None)) is None:
            raise NotFoundError(key)
        return found

    @override
    def plan(self, purpose_key: str, data: NewTypeData) -> EntryTypeDTO:
        purpose = self.purpose(purpose_key)
        existing = self._types.list_all()
        fields: list[dict[str, SettingDefault]] = [
            {
                **FIELD_DEFAULTS,
                "key": field.key,
                "label": data["fields"][field.key],
                "kind": field.kind,
            }
            for field in purpose.fields
            if field.key in data["fields"]
        ]
        settings: dict[str, SettingDefault | tuple[FieldDefinitionDTO, ...]] = {
            **TYPE_DEFAULTS,
            "key": data["key"] or _key(data["label"]),
            "label": data["label"],
            "label_plural": data["label_plural"],
            "route": data["route"],
            "colour": data["colour"],
            "tint": self._schema.derive_tint(data["colour"]),
            "role": purpose.role,
            # After every type there is: the menu and the admin sort by it.
            "order": max((t.order for t in existing), default=-1) + 1,
            "allowed_parts": tuple(data["allowed_parts"]),
            "required_parts": tuple(data["required_parts"]),
            "in_menu": data["in_menu"],
            "has_detail_page": data["has_detail_page"],
            "door_enabled": data["door_enabled"],
            "fields": tuple(
                FieldDefinitionDTO.model_validate(field) for field in fields
            ),
        }
        planned = EntryTypeDTO.model_validate(settings)
        errors = type_errors(self._schema, planned)
        for other in existing:
            if other.key == planned.key:
                errors.append(f"A type with the key {planned.key!r} already exists.")
            if other.route == planned.route:
                errors.append(f"/{planned.route}/ already lists {other.label_plural}.")
        if errors:
            raise TypeValidationError(errors)
        return planned

    @override
    def create(self, purpose_key: str, data: NewTypeData) -> EntryTypeDTO:
        planned = self.plan(purpose_key, data)
        self._types.save_all([type_to_data(planned)])
        return planned
