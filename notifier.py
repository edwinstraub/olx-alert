"""Deliver new-listing notifications through a pluggable channel.

``Notifier`` is the interface; ``EmailNotifier`` (Gmail SMTP) is the first
implementation. Adding a channel means adding a ``Notifier`` subclass and
selecting it in config — nothing else changes.
"""

from __future__ import annotations

import os
import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


class Notifier(ABC):
    """Send a notification for a list of new listings."""

    @abstractmethod
    def send(self, new_listings) -> None:  # pragma: no cover - interface
        ...


def render_subject(listings) -> str:
    count = len(listings)
    noun = "listing" if count == 1 else "listings"
    return f"🏍️ {count} new motorcycle {noun} on OLX"


def render_body(listings) -> str:
    blocks = [_render_listing(listing) for listing in listings]
    return "\n\n".join(blocks)


def _render_listing(listing) -> str:
    # Title (fall back to the URL if absent), then any best-effort fields that
    # are present, then the direct link. Missing fields are simply omitted.
    lines = [listing.title or "(untitled listing)"]
    for value in (listing.price, listing.location, listing.posted_time):
        if value:
            lines.append(value)
    lines.append(listing.url)
    return "\n".join(lines)


class EmailNotifier(Notifier):
    """Send notifications by email over Gmail SMTP (App Password)."""

    def __init__(self, recipient, user, password, host=SMTP_HOST, port=SMTP_PORT,
                 transport=None):
        self.recipient = recipient
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self._transport = transport or self._smtp_transport

    def send(self, new_listings) -> None:
        message = EmailMessage()
        message["Subject"] = render_subject(new_listings)
        message["From"] = self.user
        message["To"] = self.recipient
        message.set_content(render_body(new_listings))
        self._transport(message)

    def _smtp_transport(self, message) -> None:
        with smtplib.SMTP(self.host, self.port) as server:
            server.starttls()
            server.login(self.user, self.password)
            server.send_message(message)


def get_notifier(config) -> Notifier:
    """Build the configured notifier. Secrets come from the environment."""
    kind = config.get("notifier", "email")
    if kind == "email":
        return EmailNotifier(
            recipient=config["recipient_email"],
            user=os.environ["SMTP_USER"],
            password=os.environ["SMTP_PASS"],
        )
    raise ValueError(f"unknown notifier channel: {kind!r}")
