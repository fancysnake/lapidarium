"""The newsletter and contact forms."""

from http import HTTPStatus

import pytest
from django.core import mail

from lapidarium.gates.web.django.rendering import sender
from lapidarium.links.db.django.models import Profile
from lapidarium.pacts import DeliveryError

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]

MESSAGE = {"name": "Ola", "email": "ola@example.com", "message": "Hi!", "website": ""}


def test_newsletter_form(site):
    response = site.get("/newsletter/")

    assert response.status_code == HTTPStatus.OK
    assert not response.context["problem"]
    assert response.context["subscribed"] is False
    assert not response.context["form"].is_bound


def test_subscribing_redirects_to_the_thanks(site, caplog):
    response = site.post("/newsletter/", {"email": "ola@example.com"})

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"] == "/newsletter/?subscribed=1"
    assert "Newsletter subscription: ola@example.com" in caplog.text
    thanks = site.get(response["Location"])
    assert thanks.context["subscribed"] is True
    assert "check your inbox" in thanks.text


def test_a_bot_subscription_is_thanked_and_ignored(site, caplog):
    response = site.post(
        "/newsletter/", {"email": "bot@example.com", "website": "http://spam"}
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"] == "/newsletter/?subscribed=1"
    assert "bot@example.com" not in caplog.text


def test_a_bad_address_is_shown_back(site):
    response = site.post("/newsletter/", {"email": "nope"})

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors == {
        "email": ["Enter a valid email address."]
    }
    assert 'value="nope"' in response.text


def test_too_many_subscriptions_are_refused(site):
    for _ in range(5):
        site.post("/newsletter/", {"email": "ola@example.com"})

    response = site.post("/newsletter/", {"email": "ola@example.com"})

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert "lot of tries" in response.context["problem"]
    assert "lot of tries" in response.text


def test_a_provider_failure_is_reported(site, monkeypatch):
    def fail(_self, _email):
        raise DeliveryError

    monkeypatch.setattr("lapidarium.links.newsletter.log.LogNewsletter.subscribe", fail)

    response = site.post("/newsletter/", {"email": "ola@example.com"})

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    assert "went wrong" in response.context["problem"]
    assert "went wrong" in response.text


def test_contact_form(site):
    response = site.get("/contact/")

    assert response.status_code == HTTPStatus.OK
    assert not response.context["problem"]
    assert response.context["sent"] is False


def test_writing_mails_the_profile(site, mailoutbox):
    response = site.post("/contact/", MESSAGE, HTTP_X_FORWARDED_FOR="9.9.9.9, 1.2.3.4")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"] == "/contact/?sent=1"
    [message] = mailoutbox
    assert message.subject == "Contact form: Ola"
    assert message.body == "Hi!"
    assert message.to == ["mira@example.com"]
    assert message.reply_to == ["ola@example.com"]
    assert "on its way" in site.get(response["Location"]).text


def test_a_bot_is_thanked_and_ignored(site, mailoutbox):
    response = site.post("/contact/", {**MESSAGE, "website": "http://spam"})

    assert response.status_code == HTTPStatus.FOUND
    assert mailoutbox == []


def test_an_incomplete_message_is_shown_back(site):
    response = site.post("/contact/", {**MESSAGE, "message": ""})

    assert response.status_code == HTTPStatus.OK
    assert list(response.context["form"].errors) == ["message"]
    assert "This field is required." in response.text


def test_too_many_messages_are_refused(site):
    for _ in range(5):
        site.post("/contact/", MESSAGE)

    response = site.post("/contact/", MESSAGE)

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert "lot of tries" in response.context["problem"]


def test_a_mail_failure_is_reported(site, monkeypatch):
    def fail(*_args, **_kwargs):
        raise OSError

    monkeypatch.setattr(mail.EmailMessage, "send", fail)

    response = site.post("/contact/", MESSAGE)

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    assert "went wrong" in response.context["problem"]


def test_no_contact_page_without_an_address(site):
    Profile.objects.update(email="")

    assert site.get("/contact/").status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize(
    ("hops", "forwarded", "expected"),
    (
        (0, "9.9.9.9", "127.0.0.1"),
        (1, "", "127.0.0.1"),
        (1, "9.9.9.9, 1.2.3.4", "1.2.3.4"),
        (2, "9.9.9.9, 1.2.3.4, 5.6.7.8", "1.2.3.4"),
        (2, "1.2.3.4", "127.0.0.1"),
    ),
)
def test_sender_trusts_only_the_proxy_hops(*, rf, settings, hops, forwarded, expected):
    settings.TRUSTED_PROXY_HOPS = hops

    assert sender(rf.get("/", HTTP_X_FORWARDED_FOR=forwarded)) == expected
