"""Development stand-in for a newsletter provider: subscriptions go to the log."""

from __future__ import annotations

import logging
from typing import override

from lapidarium.pacts import NewsletterProtocol

logger = logging.getLogger(__name__)


class LogNewsletter(NewsletterProtocol):
    @override
    def subscribe(self, email: str) -> None:
        logger.info("Newsletter subscription: %s", email)
