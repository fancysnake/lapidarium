"""Changes to a type that exists, and what they do to its entries."""

from typing import TYPE_CHECKING, override

from lapidarium.mills.content import field_to_data, type_to_data
from lapidarium.mills.schema import label_key, no_key_error, type_clashes, type_errors
from lapidarium.pacts.content import (
    FIELD_DEFAULTS,
    PLAIN_FIELD_KINDS,
    EntryTypeDTO,
    FieldDefinitionDTO,
    NotFoundError,
    SettingDefault,
)
from lapidarium.pacts.purposes import (
    ConsentNeededError,
    NewFieldData,
    TypeChangeData,
    TypeChangeDTO,
    TypeEffect,
    TypeEffectDTO,
    TypeValidationError,
)
from lapidarium.pacts.services import SchemaServiceProtocol, TypeChangeServiceProtocol

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

    from lapidarium.pacts.content import (
        EntryTypeData,
        EntryTypeRepositoryProtocol,
        FieldDefinitionData,
    )


def _find(types: Iterable[EntryTypeDTO], key: str) -> EntryTypeDTO:
    if (found := next((t for t in types if t.key == key), None)) is None:
        raise NotFoundError(key)
    return found


def _added_field(
    new: NewFieldData, taken: Collection[str]
) -> tuple[FieldDefinitionData | None, list[str]]:
    """Return the field `new` asks for, `None` without a key, and what is wrong."""
    if not (key := label_key(new["label"])):
        return None, [no_key_error(new["label"], remedy="pick another name")]
    settings: dict[str, SettingDefault] = {
        **FIELD_DEFAULTS,
        "key": key,
        "label": new["label"],
        "kind": new["kind"],
    }
    added = FieldDefinitionDTO.model_validate(settings)
    errors: list[str] = []
    if added.key in taken:
        errors.append(f"A field with the key {added.key!r} already exists.")
    if added.kind not in PLAIN_FIELD_KINDS:
        errors.append(f"A {added.kind} field needs settings only the admin has.")
    return field_to_data(added), errors


class TypeChangeService(TypeChangeServiceProtocol):
    def __init__(
        self, *, types: EntryTypeRepositoryProtocol, schema: SchemaServiceProtocol
    ) -> None:
        self._types = types
        self._schema = schema

    @override
    def entry_type(self, key: str) -> EntryTypeDTO:
        return _find(self._types.list_all(), key)

    @override
    def plan_change(self, key: str, data: TypeChangeData) -> TypeChangeDTO:
        existing = self._types.list_all()
        current = _find(existing, key)
        stored = type_to_data(current)
        fields: list[FieldDefinitionData] = [
            {**field, "label": data["labels"][field["key"]]}
            for field in stored["fields"]
        ]
        errors: list[str] = []
        if (new := data["added"]) is not None:
            added, errors = _added_field(new, {f["key"] for f in fields})
            if added is not None:
                fields.append(added)
        colour = data["settings"]["colour"]
        changes: EntryTypeData = {
            **stored,
            **data["settings"],
            # A tint set by hand stays until the colour it was set for goes.
            "tint": (
                current.tint
                if colour == current.colour
                else self._schema.derive_tint(colour)
            ),
            "fields": fields,
        }
        changed = EntryTypeDTO.model_validate(changes)
        others = [t for t in existing if t.key != key]
        if errors := [
            *type_errors(self._schema, changed),
            *errors,
            *type_clashes(changed, others),
        ]:
            raise TypeValidationError(errors)
        effects = self._effects(current, changed)
        return TypeChangeDTO(entry_type=changed, effects=effects)

    @override
    def change(self, key: str, data: TypeChangeData, *, consent: str) -> None:
        planned = self.plan_change(key, data)
        if planned.consent != consent:
            raise ConsentNeededError(planned)
        self._types.save_all([type_to_data(planned.entry_type)])

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
