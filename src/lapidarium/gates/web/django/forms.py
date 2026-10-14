from django import forms
from django.utils.translation import gettext_lazy as _

_MESSAGE_MAX_LENGTH = 5000


class NewsletterForm(forms.Form):
    email = forms.EmailField(label=_("Your e-mail"))
    # Hidden from people; whatever lands here was filled in by a bot.
    website = forms.CharField(required=False)


class ContactForm(forms.Form):
    name = forms.CharField(label=_("Your name"), max_length=100)
    email = forms.EmailField(label=_("Your e-mail"))
    message = forms.CharField(
        label=_("Message"), max_length=_MESSAGE_MAX_LENGTH, widget=forms.Textarea
    )
    website = forms.CharField(required=False)
