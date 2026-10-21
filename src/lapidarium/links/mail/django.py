from __future__ import annotations

from typing import TYPE_CHECKING, override

from django.core.mail import EmailMessage

from lapidarium.pacts.outreach import DeliveryError, MailerProtocol

if TYPE_CHECKING:
    from lapidarium.pacts.outreach import MailData


class DjangoMailer(MailerProtocol):
    """Sends through whatever backend `EMAIL_URL` configures."""

    @override
    def send(self, mail: MailData) -> None:
        message = EmailMessage(
            subject=mail["subject"],
            body=mail["body"],
            to=[mail["to"]],
            reply_to=[mail["reply_to"]],
        )
        try:
            message.send()
        except OSError as exc:
            msg = f"Could not mail {mail['to']!r}."
            raise DeliveryError(msg) from exc
