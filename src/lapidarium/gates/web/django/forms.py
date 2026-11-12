from typing import TYPE_CHECKING

from django import forms
from django.utils.translation import gettext_lazy as _

from lapidarium.pacts.content import TYPE_DEFAULTS, PartKind
from lapidarium.pacts.theme import HEX_COLOUR

if TYPE_CHECKING:
    from django.http import QueryDict
    from django.utils.functional import _StrOrPromise

    from lapidarium.pacts.purposes import NewTypeData, PurposeDTO

_MESSAGE_MAX_LENGTH = 5000
_NAME_MAX_LENGTH = 100
_PART_CHOICES = [(kind.value, kind.value.capitalize()) for kind in PartKind]
_STARTER = "field_"


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


def _parts(label: _StrOrPromise) -> forms.MultipleChoiceField:
    return forms.MultipleChoiceField(
        label=label,
        choices=_PART_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )


class NewTypeForm(forms.Form):
    """A type to create from a purpose, opening on what the purpose suggests."""

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
    key = forms.SlugField(
        label=_("Key"),
        max_length=_NAME_MAX_LENGTH,
        required=False,
        widget=_text(),
        help_text=_("Names the type in exports. Made from the name when blank."),
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
        )
        self._starters = [field.key for field in purpose.fields]
        for field in purpose.fields:
            self.fields[_STARTER + field.key] = forms.CharField(
                label=field.label,
                initial=field.label,
                max_length=_NAME_MAX_LENGTH,
                required=False,
                widget=_text(),
            )

    @property
    def starters(self) -> list[forms.BoundField]:
        return [self[_STARTER + key] for key in self._starters]

    def to_data(self) -> NewTypeData:
        """Return the cleaned type; read after `is_valid()`."""
        data = self.cleaned_data
        return {
            "key": data["key"],
            "label": data["label"],
            "label_plural": data["label_plural"],
            "route": data["route"],
            "colour": data["colour"],
            "fields": {
                field.name.removeprefix(_STARTER): label
                for field in self.starters
                if (label := data[field.name].strip())
            },
            "allowed_parts": [PartKind(kind) for kind in data["allowed_parts"]],
            "required_parts": [PartKind(kind) for kind in data["required_parts"]],
            "in_menu": data["in_menu"],
            "has_detail_page": data["has_detail_page"],
            "door_enabled": data["door_enabled"],
        }
