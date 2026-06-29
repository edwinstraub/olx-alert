import pytest

import notifier
from notifier import Notifier, EmailNotifier
from olx import Listing


def sample():
    return [
        Listing(
            id="kHuzM",
            title="Honda CBR 600RR",
            price="5 500 €",
            location="Cluj-Napoca, Cluj",
            url="https://www.olx.ro/d/oferta/honda-cbr-600rr-IDkHuzM.html",
            posted_time="2026-06-29T10:15:00+03:00",
        ),
        Listing(
            id="kAZhr",
            title="KTM Duke 125",
            url="https://www.olx.ro/d/oferta/ktm-duke-125-IDkAZhr.html",
        ),
    ]


# --- subject -----------------------------------------------------------------

def test_subject_summarizes_count_plural():
    assert "2" in notifier.render_subject(sample())


def test_subject_singular():
    subject = notifier.render_subject(sample()[:1])
    assert "1" in subject


# --- body --------------------------------------------------------------------

def test_body_lists_each_listing_with_link():
    body = notifier.render_body(sample())
    assert "Honda CBR 600RR" in body
    assert "5 500 €" in body
    assert "Cluj-Napoca, Cluj" in body
    assert "https://www.olx.ro/d/oferta/honda-cbr-600rr-IDkHuzM.html" in body
    # second listing present with its link
    assert "KTM Duke 125" in body
    assert "https://www.olx.ro/d/oferta/ktm-duke-125-IDkAZhr.html" in body


def test_body_renders_partial_fields_without_blank_labels():
    # The KTM has no price/location/posted_time; rendering must not crash and
    # must still include its title and link.
    body = notifier.render_body(sample())
    assert "KTM Duke 125" in body


# --- EmailNotifier (transport injected; nothing actually sent) ---------------

def test_email_notifier_sends_message_with_subject_and_body():
    sent = {}

    def transport(msg):
        sent["msg"] = msg

    EmailNotifier(
        recipient="me@example.com",
        user="bot@gmail.com",
        password="secret",
        transport=transport,
    ).send(sample())

    msg = sent["msg"]
    assert msg["To"] == "me@example.com"
    assert msg["From"] == "bot@gmail.com"
    assert "2" in msg["Subject"]
    assert "Honda CBR 600RR" in msg.get_content()


def test_email_notifier_propagates_transport_failure():
    def transport(msg):
        raise OSError("smtp down")

    with pytest.raises(OSError):
        EmailNotifier(
            recipient="me@example.com",
            user="bot@gmail.com",
            password="secret",
            transport=transport,
        ).send(sample())


# --- pluggable selection -----------------------------------------------------

def test_get_notifier_returns_email_by_default(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "bot@gmail.com")
    monkeypatch.setenv("SMTP_PASS", "secret")
    n = notifier.get_notifier({"recipient_email": "me@example.com"})
    assert isinstance(n, EmailNotifier)
    assert isinstance(n, Notifier)
    assert n.recipient == "me@example.com"
    assert n.user == "bot@gmail.com"


def test_get_notifier_rejects_unknown_channel():
    with pytest.raises(ValueError):
        notifier.get_notifier({"notifier": "carrier-pigeon"})
