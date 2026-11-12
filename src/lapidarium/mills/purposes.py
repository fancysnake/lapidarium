"""The site's types by purpose: new types from a purpose, changes to a type."""

import re
from typing import TYPE_CHECKING, override

from lapidarium.mills.content import field_to_data, type_to_data
from lapidarium.mills.schema import slug_errors, type_errors
from lapidarium.pacts.content import (
    FIELD_DEFAULTS,
    PLAIN_FIELD_KINDS,
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
    TypeChangeData,
    TypeChangeDTO,
    TypeEffect,
    TypeEffectDTO,
    TypeUseDTO,
    TypeValidationError,
)
from lapidarium.pacts.services import PurposeServiceProtocol, SchemaServiceProtocol
from lapidarium.specs import MECHANIC_NAMES, PURPOSES

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

    from lapidarium.pacts.content import (
        EntryTypeData,
        EntryTypeRepositoryProtocol,
        FieldDefinitionData,
    )


def _key(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def _find(types: Iterable[EntryTypeDTO], key: str) -> EntryTypeDTO:
    if (found := next((t for t in types if t.key == key), None)) is None:
        raise NotFoundError(key)
    return found


def _clashes(planned: EntryTypeDTO, others: Iterable[EntryTypeDTO]) -> list[str]:
    """Keys and addresses `planned` shares with another type."""
    errors: list[str] = []
    for other in others:
        if other.key == planned.key:
            errors.append(f"A type with the key {planned.key!r} already exists.")
        if other.route == planned.route:
            errors.append(f"/{planned.route}/ already lists {other.label_plural}.")
    return errors


def _new_field_errors(added: FieldDefinitionDTO, taken: Collection[str]) -> list[str]:
    errors = slug_errors("Field key", added.key)
    if added.key in taken:
        errors.append(f"A field with the key {added.key!r} already exists.")
    if added.kind not in PLAIN_FIELD_KINDS:
        errors.append(f"A {added.kind} field needs settings only the admin has.")
    return errors


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
        errors = [*type_errors(self._schema, planned), *_clashes(planned, existing)]
        if errors:
            raise TypeValidationError(errors)
        return planned

    @override
    def create(self, purpose_key: str, data: NewTypeData) -> EntryTypeDTO:
        planned = self.plan(purpose_key, data)
        self._types.save_all([type_to_data(planned)])
        return planned

    @override
    def entry_type(self, key: str) -> EntryTypeDTO:
        return _find(self._types.list_all(), key)

    @override
    def plan_change(self, key: str, data: TypeChangeData) -> TypeChangeDTO:
        existing = self._types.list_all()
        current = _find(existing, key)
        stored = type_to_data(current)
        fields: list[FieldDefinitionData] = [
            {**field, "label": data["fields"].get(field["key"], field["label"])}
            for field in stored["fields"]
        ]
        errors: list[str] = []
        for label, kind in data["added"].items():
            settings: dict[str, SettingDefault] = {
                **FIELD_DEFAULTS,
                "key": _key(label),
                "label": label,
                "kind": kind,
            }
            added = FieldDefinitionDTO.model_validate(settings)
            errors.extend(_new_field_errors(added, {f["key"] for f in fields}))
            fields.append(field_to_data(added))
        colour = data["colour"]
        changes: EntryTypeData = {
            **stored,
            "label": data["label"],
            "label_plural": data["label_plural"],
            "route": data["route"],
            "colour": colour,
            # A tint set by hand stays until the colour it was set for goes.
            "tint": (
                current.tint
                if colour == current.colour
                else self._schema.derive_tint(colour)
            ),
            "allowed_parts": data["allowed_parts"],
            "required_parts": data["required_parts"],
            "in_menu": data["in_menu"],
            "has_detail_page": data["has_detail_page"],
            "door_enabled": data["door_enabled"],
            "fields": fields,
        }
        changed = EntryTypeDTO.model_validate(changes)
        errors = [
            *type_errors(self._schema, changed),
            *errors,
            *_clashes(changed, [t for t in existing if t.key != key]),
        ]
        if errors:
            raise TypeValidationError(errors)
        return TypeChangeDTO(
            entry_type=changed, effects=self._effects(current, changed), saved=False
        )

    @override
    def change(self, key: str, data: TypeChangeData, *, consent: str) -> TypeChangeDTO:
        planned = self.plan_change(key, data)
        if planned.consent != consent:
            return planned
        self._types.save_all([type_to_data(planned.entry_type)])
        return TypeChangeDTO(
            entry_type=planned.entry_type, effects=planned.effects, saved=True
        )

    def _effects(
        self, current: EntryTypeDTO, changed: EntryTypeDTO
    ) -> tuple[TypeEffectDTO, ...]:
        """Effects on at least one entry, in the order the form asks."""
        if not (total := self._types.entry_counts()[current.key]):
            return ()
        holders = self._types.part_holders(current.key)
        effects: list[TypeEffectDTO] = []
        if current.has_detail_page != changed.has_detail_page:
            kind = (
                TypeEffect.PAGE_GAINED
                if changed.has_detail_page
                else TypeEffect.PAGE_LOST
            )
            effects.append(TypeEffectDTO(kind=kind, entries=total))
        elif changed.has_detail_page and changed.route != current.route:
            effects.append(TypeEffectDTO(kind=TypeEffect.MOVED, entries=total))
        effects.extend(
            TypeEffectDTO(
                kind=TypeEffect.PART_REFUSED, entries=holders.get(part, 0), part=part
            )
            for part in current.allowed_parts
            if part not in changed.allowed_parts
        )
        effects.extend(
            TypeEffectDTO(
                kind=TypeEffect.PART_MISSING,
                entries=total - holders.get(part, 0),
                part=part,
            )
            for part in changed.required_parts
            if part not in current.required_parts
        )
        return tuple(effect for effect in effects if effect.entries)
