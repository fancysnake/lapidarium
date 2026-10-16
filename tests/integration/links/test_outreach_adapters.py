import datetime as dt
import hashlib
import json

import httpx
import pytest
from django.core import mail
from django.core.cache import cache

from lapidarium.links.mail.django import DjangoMailer
from lapidarium.links.newsletter.log import LogNewsletter
from lapidarium.links.newsletter.mailchimp import MailchimpNewsletter
from lapidarium.links.throttle.django import CacheThrottle
from lapidarium.pacts import DeliveryError

HOUR = dt.timedelta(hours=1)


def _mailchimp(handler):
    return MailchimpNewsletter(
        api_key="secret-us21", list_id="abc", transport=httpx.MockTransport(handler)
    )


def test_mailchimp_upserts_a_pending_member():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={})

    _mailchimp(handler).subscribe("Ola@Example.com")

    assert len(requests) == 1
    request = requests[0]
    member = hashlib.md5(b"ola@example.com", usedforsecurity=False).hexdigest()
    assert request.method == "PUT"
    assert str(request.url) == (
        f"https://us21.api.mailchimp.com/3.0/lists/abc/members/{member}"
    )
    assert json.loads(request.content) == {
        "email_address": "Ola@Example.com",
        "status_if_new": "pending",
    }
    assert request.headers["authorization"].startswith("Basic ")


def _refuse(_request):
    return httpx.Response(400, json={"title": "Invalid Resource"})


def _unreachable(request):
    msg = "down"
    raise httpx.ConnectError(msg, request=request)


@pytest.mark.parametrize("respond", (_refuse, _unreachable))
def test_mailchimp_failures_are_delivery_errors(respond):
    with pytest.raises(DeliveryError):
        _mailchimp(respond).subscribe("ola@example.com")


def test_log_newsletter_logs(caplog):
    LogNewsletter().subscribe("ola@example.com")

    assert "Newsletter subscription: ola@example.com" in caplog.text


def test_mailer_sends(mailoutbox):
    DjangoMailer().send(
        {"subject": "Hi", "body": "Body", "to": "a@example.com", "reply_to": "b@x.io"}
    )

    [message] = mailoutbox
    assert (message.subject, message.body, message.to, message.reply_to) == (
        "Hi",
        "Body",
        ["a@example.com"],
        ["b@x.io"],
    )


def test_mailer_failures_are_delivery_errors(monkeypatch):
    def fail(*_args, **_kwargs):
        raise OSError

    monkeypatch.setattr(mail.EmailMessage, "send", fail)

    with pytest.raises(DeliveryError):
        DjangoMailer().send({"subject": "", "body": "", "to": "a@x.io", "reply_to": ""})


def test_throttle_allows_up_to_the_limit_per_key():
    throttle = CacheThrottle()

    allowed = [throttle.allow("t:a", limit=2, window=HOUR) for _ in range(3)]

    assert allowed == [True, True, False]
    assert throttle.allow("t:b", limit=2, window=HOUR) is True


def test_throttle_opens_a_new_window_when_the_old_one_vanished(monkeypatch):
    def gone(_key):
        raise ValueError

    monkeypatch.setattr(cache, "incr", gone)

    assert CacheThrottle().allow("t:c", limit=1, window=HOUR) is True
    assert cache.get("throttle:t:c") == 1
