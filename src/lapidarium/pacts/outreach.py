"""Reaching the owner and their readers: contact mail and the newsletter."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, TypedDict

if TYPE_CHECKING:
    import datetime as dt


class NewsletterBackend(StrEnum):
    LOG = "log"
    MAILCHIMP = "mailchimp"


class RateLimitedError(Exception):
    """The sender has used up their attempts for now."""


class DeliveryError(Exception):
    """A mail or newsletter provider did not take the message."""


class ContactData(TypedDict):
    name: str
    email: str
    message: str


class MailData(TypedDict):
    subject: str
    body: str
    to: str
    reply_to: str


class NewsletterProtocol(Protocol):
    def subscribe(self, email: str) -> None:
        """Add `email`, or leave an existing subscriber be; `DeliveryError` else."""


class MailerProtocol(Protocol):
    def send(self, mail: MailData) -> None:
        """Send one message; `DeliveryError` when it cannot."""


class ThrottleProtocol(Protocol):
    def allow(self, key: str, *, limit: int, window: dt.timedelta) -> bool:
        """Count one attempt under `key`; False once `limit` are used in `window`."""
