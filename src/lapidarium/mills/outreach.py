"""Reaching the person behind the site: the newsletter and the contact form."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from lapidarium.pacts.content import NotFoundError
from lapidarium.pacts.outreach import RateLimitedError
from lapidarium.pacts.services import OutreachServiceProtocol
from lapidarium.specs import OUTREACH_LIMIT, OUTREACH_WINDOW

if TYPE_CHECKING:
    from lapidarium.pacts.content import ProfileRepositoryProtocol
    from lapidarium.pacts.outreach import (
        ContactData,
        MailerProtocol,
        NewsletterProtocol,
        ThrottleProtocol,
    )


class OutreachService(OutreachServiceProtocol):
    def __init__(
        self,
        *,
        newsletter: NewsletterProtocol,
        mailer: MailerProtocol,
        throttle: ThrottleProtocol,
        profile: ProfileRepositoryProtocol,
    ) -> None:
        self._newsletter = newsletter
        self._mailer = mailer
        self._throttle = throttle
        self._profile = profile

    def _recipient(self) -> str:
        profile = self._profile.get()
        return profile.email if profile else ""

    def _count(self, action: str, sender: str) -> None:
        if not self._throttle.allow(
            f"{action}:{sender}", limit=OUTREACH_LIMIT, window=OUTREACH_WINDOW
        ):
            raise RateLimitedError(sender)

    @override
    def can_contact(self) -> bool:
        return bool(self._recipient())

    @override
    def subscribe(self, email: str, *, sender: str) -> None:
        self._count("newsletter", sender)
        self._newsletter.subscribe(email)

    @override
    def contact(self, message: ContactData, *, sender: str) -> None:
        if not (recipient := self._recipient()):
            msg = "profile e-mail"
            raise NotFoundError(msg)
        self._count("contact", sender)
        self._mailer.send(
            {
                "subject": f"Contact form: {message['name']}",
                "body": message["message"],
                "to": recipient,
                "reply_to": message["email"],
            }
        )
