from unittest.mock import MagicMock

import pytest

from lapidarium.mills.outreach import OutreachService
from lapidarium.pacts import NotFoundError, ProfileDTO, RateLimitedError
from lapidarium.specs import OUTREACH_LIMIT, OUTREACH_WINDOW


def _profile(email="mira@example.com"):
    return ProfileDTO(
        name="Mira", handle="", tagline="", photo=None, bio="", email=email
    )


def _service(profile=None, *, allowed=True):
    deps = MagicMock()
    deps.profile.get.return_value = profile
    deps.throttle.allow.return_value = allowed
    service = OutreachService(
        newsletter=deps.newsletter,
        mailer=deps.mailer,
        throttle=deps.throttle,
        profile=deps.profile,
    )
    return service, deps


def _message():
    return {"name": "Ola", "email": "ola@example.com", "message": "Hi!"}


@pytest.mark.parametrize(
    ("profile", "expected"),
    ((_profile(), True), (_profile(email=""), False), (None, False)),
)
def test_can_contact_only_with_an_address(profile, expected):
    service, _ = _service(profile)

    assert service.can_contact() is expected


def test_subscribe_counts_the_attempt_and_subscribes():
    service, deps = _service()

    service.subscribe("ola@example.com", sender="1.2.3.4")

    deps.throttle.allow.assert_called_once_with(
        "newsletter:1.2.3.4", limit=OUTREACH_LIMIT, window=OUTREACH_WINDOW
    )
    deps.newsletter.subscribe.assert_called_once_with("ola@example.com")


def test_subscribe_too_many_attempts_are_refused():
    service, deps = _service(allowed=False)

    with pytest.raises(RateLimitedError):
        service.subscribe("ola@example.com", sender="1.2.3.4")
    deps.newsletter.subscribe.assert_not_called()


def test_contact_mails_the_profile():
    service, deps = _service(_profile())

    service.contact(_message(), sender="1.2.3.4")

    deps.throttle.allow.assert_called_once_with(
        "contact:1.2.3.4", limit=OUTREACH_LIMIT, window=OUTREACH_WINDOW
    )
    deps.mailer.send.assert_called_once_with(
        {
            "subject": "Contact form: Ola",
            "body": "Hi!",
            "to": "mira@example.com",
            "reply_to": "ola@example.com",
        }
    )


def test_contact_without_an_address_there_is_no_one_to_mail():
    service, deps = _service(None)

    with pytest.raises(NotFoundError):
        service.contact(_message(), sender="1.2.3.4")
    deps.mailer.send.assert_not_called()


def test_contact_too_many_attempts_are_refused():
    service, deps = _service(_profile(), allowed=False)

    with pytest.raises(RateLimitedError):
        service.contact(_message(), sender="1.2.3.4")
    deps.mailer.send.assert_not_called()
