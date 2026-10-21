"""Mailchimp Marketing API over plain HTTP, no SDK."""

from __future__ import annotations

import hashlib
from typing import override

import httpx

from lapidarium.pacts.outreach import DeliveryError, NewsletterProtocol

_TIMEOUT = 10.0


class MailchimpNewsletter(NewsletterProtocol):
    """New members join as pending, so Mailchimp sends the opt-in mail itself."""

    def __init__(
        self,
        *,
        api_key: str,
        list_id: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        # Keys end in the data centre that serves the account: `…-us21`.
        data_centre = api_key.rpartition("-")[2]
        self._members = (
            f"https://{data_centre}.api.mailchimp.com/3.0/lists/{list_id}/members"
        )
        self._client = httpx.Client(
            auth=("lapidarium", api_key), timeout=_TIMEOUT, transport=transport
        )

    @override
    def subscribe(self, email: str) -> None:
        # Members are addressed by the MD5 of the lowercased address; PUT creates
        # a new one and leaves an existing one's status alone.
        member = hashlib.md5(email.lower().encode(), usedforsecurity=False).hexdigest()
        body: dict[str, str] = {"email_address": email, "status_if_new": "pending"}
        msg = f"Mailchimp did not take {email!r}."
        try:
            response = self._client.put(f"{self._members}/{member}", json=body)
        except httpx.HTTPError as exc:
            raise DeliveryError(msg) from exc
        if response.is_error:
            raise DeliveryError(msg)
