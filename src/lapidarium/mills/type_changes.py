"""Changes to a type that exists, and what they do to its entries."""

from typing import TYPE_CHECKING, override

from lapidarium.mills.content import field_to_data, type_to_data
from lapidarium.mills.schema import label_key, no_key_error, type_clashes, type_errors
from lapidarium.pacts.content import (
    FIELD_DEFAULTS,
    PLAIN_FIELD_KINDS,
    EntryTypeDTO,
    FieldDefinitionDTO,
    FieldKind,
    NotFoundError,
    SettingDefault,
    UrlKind,
)
from lapidarium.pacts.purposes import (
    ConsentNeededError,
    FieldsInUseError,
    FieldUseDTO,
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
        MetadataValue,
    )


def _find(types: Iterable[EntryTypeDTO], key: str) -> EntryTypeDTO:
    if (found := next((t for t in types if t.key == key), None)) is None:
        raise NotFoundError(key)
    return found


def _kind_errors(kind: FieldKind) -> list[str]:
    if kind in PLAIN_FIELD_KINDS:
        return []
    return [f"A {kind} field needs settings only the admin has."]


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
    errors = _kind_errors(added.kind)
    if added.key in taken:
        errors.insert(0, f"A field with the key {added.key!r} already exists.")
    return field_to_data(added), errors


def _kept_field(
    field: FieldDefinitionDTO, data: TypeChangeData
) -> tuple[FieldDefinitionData, list[str]]:
    """Return `field` under the label and kind `data` gives it, and what is wrong."""
    kept: FieldDefinitionData = {
        **field_to_data(field),
        "label": data["labels"][field.key],
    }
    if (kind := data["kinds"][field.key]) == field.kind:
        return kept, []
    # Settings of the old kind mean nothing to the new one.
    changed: FieldDefinitionData = {
        **kept,
        "kind": kind,
        "choices": [],
        "url_kind": UrlKind.ANY_HOST,
        "target_type": "",
    }
    return changed, _kind_errors(kind)


def _planned_fields(
    current: EntryTypeDTO, data: TypeChangeData
) -> tuple[list[FieldDefinitionData], list[str]]:
    """Return the fields `data` leaves the type with, and what is wrong with them."""
    removed = data["removed"]
    fields: list[FieldDefinitionData] = []
    errors: list[str] = []
    for field in current.fields:
        if field.key not in removed:
            kept, wrong = _kept_field(field, data)
            fields.append(kept)
            errors += wrong
    if (new := data["added"]) is not None:
        added, wrong = _added_field(new, {f["key"] for f in fields})
        errors += wrong
        if added is not None:
            fields.append(added)
    return fields, errors


def _holds(value: MetadataValue | None) -> bool:
    """Whether a stored value is one to lose; a switch left off is not."""
    return value is not None and value is not False and bool(str(value))


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
    def field_use(self, key: str, field_key: str) -> FieldUseDTO:
        fields = self.entry_type(key).fields
        if (field := next((f for f in fields if f.key == field_key), None)) is None:
            raise NotFoundError(field_key)
        return self._use(key, field)

    @override
    def plan_change(self, key: str, data: TypeChangeData) -> TypeChangeDTO:
        existing = self._types.list_all()
        current = _find(existing, key)
        stored = type_to_data(current)
        fields, errors = _planned_fields(current, data)
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
            # A filter on a removed field has nothing left to offer.
            "list_filters": [
                f for f in stored["list_filters"] if f not in data["removed"]
            ],
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
        if uses := self._lost_uses(current, changed):
            raise FieldsInUseError(uses)
        effects = self._effects(current, changed)
        return TypeChangeDTO(entry_type=changed, effects=effects)

    def _lost_uses(
        self, current: EntryTypeDTO, changed: EntryTypeDTO
    ) -> list[FieldUseDTO]:
        """Return the uses of the fields `changed` drops or gives another kind."""
        kinds = {field.key: field.kind for field in changed.fields}
        lossy = (f for f in current.fields if kinds.get(f.key) != f.kind)
        return [use for f in lossy if (use := self._use(current.key, f)).entries]

    def _use(self, type_key: str, field: FieldDefinitionDTO) -> FieldUseDTO:
        if field.kind == FieldKind.RELATION:
            entries = self._types.linking_entries(type_key, field.key)
        else:
            stored = self._types.field_values(type_key, field.key)
            entries = [entry for entry, value in stored if _holds(value)]
        return FieldUseDTO(field=field, entries=tuple(entries))

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
