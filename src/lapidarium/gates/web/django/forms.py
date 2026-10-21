from django import forms
from django.utils.translation import gettext_lazy as _

_MESSAGE_MAX_LENGTH = 5000


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
