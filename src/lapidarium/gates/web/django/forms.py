from typing import TYPE_CHECKING

from django import forms
from django.utils.translation import gettext_lazy as _

from lapidarium.pacts.content import (
    PLAIN_FIELD_KINDS,
    TYPE_DEFAULTS,
    FieldKind,
    PartKind,
    enum_choices,
)
from lapidarium.pacts.theme import HEX_COLOUR

if TYPE_CHECKING:
    from collections.abc import Mapping

    from django.http import QueryDict
    from django.utils.functional import _StrOrPromise

    from lapidarium.pacts.content import EntryTypeDTO, SettingDefault
    from lapidarium.pacts.purposes import (
        NewTypeData,
        PurposeDTO,
        TypeChangeData,
        TypeSettingsData,
    )

_MESSAGE_MAX_LENGTH = 5000
_NAME_MAX_LENGTH = 100
_PART_CHOICES = enum_choices(PartKind)
_FIELD = "field_"
_KIND = "kind_"
_REMOVE = "remove_"


class HoneypotForm(forms.Form):
    # Hidden from people; whatever lands here was filled in by a bot.
    website = forms.CharField(required=False)

    @property
    def caught(self) -> bool:
        """Whether a bot filled the trap; read after `is_valid()`."""
        return bool(self.cleaned_data["website"])


class NewsletterForm(HoneypotForm):
    email = forms.EmailField(label=_("Your e-mail"))


class ContactForm(HoneypotForm):
    name = forms.CharField(label=_("Your name"), max_length=100)
    email = forms.EmailField(label=_("Your e-mail"))
    message = forms.CharField(
        label=_("Message"), max_length=_MESSAGE_MAX_LENGTH, widget=forms.Textarea
    )


def _text() -> forms.TextInput:
    return forms.TextInput(attrs={"class": "input"})


def _parts(label: _StrOrPromise) -> forms.TypedMultipleChoiceField:
    return forms.TypedMultipleChoiceField(
        label=label,
        choices=_PART_CHOICES,
        coerce=PartKind,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )


class _TypeForm(forms.Form):
    """Settings both type forms hold, plus a label input per field of the type."""

    label = forms.CharField(
        label=_("Name of one"), max_length=_NAME_MAX_LENGTH, widget=_text()
    )
    label_plural = forms.CharField(
        label=_("Name of many"), max_length=_NAME_MAX_LENGTH, widget=_text()
    )
    route = forms.SlugField(
        label=_("Address"),
        max_length=_NAME_MAX_LENGTH,
        widget=_text(),
        help_text=_("The list lives at /address/ on the site."),
    )
    colour = forms.RegexField(
        rf"^{HEX_COLOUR}\Z",
        label=_("Colour"),
        widget=forms.TextInput(attrs={"type": "color"}),
    )
    allowed_parts = _parts(_("Parts an entry may hold"))
    required_parts = _parts(_("Parts an entry must hold"))
    in_menu = forms.BooleanField(label=_("Show in the menu"), required=False)
    has_detail_page = forms.BooleanField(
        label=_("Each entry has its own page"), required=False
    )
    door_enabled = forms.BooleanField(
        label=_("Show a door on the home page"), required=False
    )

    def __init__(
        self,
        data: QueryDict | None,
        *,
        initial: Mapping[str, SettingDefault | list[PartKind]],
        labels: Mapping[str, str],
        labels_required: bool,
    ) -> None:
        super().__init__(data, initial=dict(initial))
        self._labelled = list(labels)
        for key, label in labels.items():
            self.fields[_FIELD + key] = forms.CharField(
                label=label,
                initial=label,
                max_length=_NAME_MAX_LENGTH,
                required=labels_required,
                widget=_text(),
            )

    @property
    def field_labels(self) -> list[forms.BoundField]:
        return [self[_FIELD + key] for key in self._labelled]

    def _labels(self) -> dict[str, str]:
        return {
            field.name.removeprefix(_FIELD): self.cleaned_data[field.name]
            for field in self.field_labels
        }

    def _settings(self) -> TypeSettingsData:
        data = self.cleaned_data
        return {
            "colour": data["colour"],
            "label": data["label"],
            "label_plural": data["label_plural"],
            "route": data["route"],
            "allowed_parts": data["allowed_parts"],
            "required_parts": data["required_parts"],
            "in_menu": data["in_menu"],
            "has_detail_page": data["has_detail_page"],
            "door_enabled": data["door_enabled"],
        }


class NewTypeForm(_TypeForm):
    """A type to create from a purpose, opening on what the purpose suggests."""

    key = forms.SlugField(
        label=_("Key"),
        max_length=_NAME_MAX_LENGTH,
        required=False,
        widget=_text(),
        help_text=_("Names the type in exports. Made from the name when blank."),
    )

    def __init__(self, data: QueryDict | None, *, purpose: PurposeDTO) -> None:
        super().__init__(
            data,
            initial={
                "label": purpose.label,
                "label_plural": purpose.label_plural,
                "route": purpose.route,
                "colour": TYPE_DEFAULTS["colour"],
                # A purpose never narrows the media an entry may hold.
                "allowed_parts": list(PartKind),
                "in_menu": TYPE_DEFAULTS["in_menu"],
                "has_detail_page": TYPE_DEFAULTS["has_detail_page"],
                "door_enabled": TYPE_DEFAULTS["door_enabled"],
            },
            labels={field.key: field.label for field in purpose.fields},
            labels_required=False,
        )

    def to_data(self) -> NewTypeData:
        """Return the cleaned type; read after `is_valid()`."""
        return {
            "settings": self._settings(),
            "key": self.cleaned_data["key"],
            "labels": {key: label for key, label in self._labels().items() if label},
        }


class ChangeTypeForm(_TypeForm):
    """New settings for a type, opening on the ones it has."""

    new_field_label = forms.CharField(
        label=_("Name of a new field"),
        max_length=_NAME_MAX_LENGTH,
        required=False,
        widget=_text(),
        help_text=_("Leave blank to add none."),
    )
    new_field_kind = forms.ChoiceField(
        label=_("Kind of the new field"),
        choices=enum_choices(PLAIN_FIELD_KINDS),
        initial=FieldKind.TEXT.value,
        widget=forms.Select(attrs={"class": "input"}),
    )

    def __init__(self, data: QueryDict | None, *, entry_type: EntryTypeDTO) -> None:
        super().__init__(
            data,
            initial={
                "label": entry_type.label,
                "label_plural": entry_type.label_plural,
                "route": entry_type.route,
                "colour": entry_type.colour,
                "allowed_parts": list(entry_type.allowed_parts),
                "required_parts": list(entry_type.required_parts),
                "in_menu": entry_type.in_menu,
                "has_detail_page": entry_type.has_detail_page,
                "door_enabled": entry_type.door_enabled,
            },
            labels={field.key: field.label for field in entry_type.fields},
            labels_required=True,
        )
        for field in entry_type.fields:
            # A choice or relation field keeps its kind, or takes a plain one.
            kinds = dict.fromkeys((field.kind, *PLAIN_FIELD_KINDS))
            named = {"field": field.label}
            self.fields[_KIND + field.key] = forms.ChoiceField(
                label=_("Kind of “%(field)s”") % named,
                choices=enum_choices(kinds),
                initial=field.kind.value,
                widget=forms.Select(attrs={"class": "input"}),
            )
            self.fields[_REMOVE + field.key] = forms.BooleanField(
                label=_("Remove “%(field)s”") % named, required=False
            )

    @property
    def field_rows(
        self,
    ) -> list[tuple[str, forms.BoundField, forms.BoundField, forms.BoundField]]:
        """The key, label, kind and removal inputs of each field of the type."""
        return [
            (key, self[_FIELD + key], self[_KIND + key], self[_REMOVE + key])
            for key in self._labelled
        ]

    def to_data(self) -> TypeChangeData:
        """Return the cleaned settings; read after `is_valid()`."""
        data = self.cleaned_data
        label = data["new_field_label"]
        kind = FieldKind(data["new_field_kind"])
        rows = self.field_rows
        return {
            "settings": self._settings(),
            "labels": self._labels(),
            "kinds": {key: FieldKind(data[kind.name]) for key, _, kind, _ in rows},
            "removed": [key for key, *_, remove in rows if data[remove.name]],
            "added": {"label": label, "kind": kind} if label else None,
        }
