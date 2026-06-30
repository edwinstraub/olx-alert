"""Fetch and parse motorcycle listings from an OLX.ro search URL.

Correctness depends only on the stable alphanumeric listing ID embedded in each
listing URL (e.g. ``.../d/oferta/...-IDkAZhr.html``). Title, price, location and
posted time are best-effort and used only to render notifications.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

# OLX listing URLs end in ``-ID<alphanumeric>.html``.
_ID_RE = re.compile(r"-ID([A-Za-z0-9]+)\.html")

# OLX returns 403 for unfamiliar clients; present a browser-like User-Agent.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
}

_TIMEOUT = 20


class FetchError(Exception):
    """Raised when listings could not be fetched or parsed for a search URL."""


@dataclass
class Listing:
    """A single OLX listing. Only ``id`` is required for correctness."""

    id: str
    title: str = ""
    price: str = ""
    location: str = ""
    url: str = ""
    posted_time: str = ""


def extract_id(url: str) -> str | None:
    """Return the stable alphanumeric ID from a listing URL, or None."""
    if not url:
        return None
    match = _ID_RE.search(url)
    return match.group(1) if match else None


def parse_listings_json(data: dict) -> list[Listing]:
    """Parse OLX's structured JSON offers into Listings (best-effort fields)."""
    listings: list[Listing] = []
    seen: set[str] = set()
    for offer in data.get("data", []) or []:
        url = offer.get("url", "") or ""
        listing_id = extract_id(url)
        if not listing_id or listing_id in seen:
            continue
        seen.add(listing_id)
        listings.append(
            Listing(
                id=listing_id,
                title=offer.get("title", "") or "",
                price=_json_price(offer),
                location=_json_location(offer),
                url=url,
                posted_time=offer.get("created_time") or "",
            )
        )
    return listings


def _json_price(offer: dict) -> str:
    for param in offer.get("params", []) or []:
        if param.get("key") == "price":
            value = param.get("value") or {}
            return value.get("label", "") or ""
    return ""


def _json_location(offer: dict) -> str:
    location = offer.get("location") or {}
    city = (location.get("city") or {}).get("name", "")
    region = (location.get("region") or {}).get("name", "")
    parts = [p for p in (city, region) if p and p != city] if city else []
    if city:
        return ", ".join([city] + parts)
    return region or ""


def parse_listings_html(html: str) -> list[Listing]:
    """Parse an OLX HTML search page into Listings (best-effort fields)."""
    soup = BeautifulSoup(html, "html.parser")
    listings: list[Listing] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        listing_id = extract_id(anchor["href"])
        if not listing_id or listing_id in seen:
            continue
        seen.add(listing_id)
        card = _enclosing_card(anchor)
        listings.append(
            Listing(
                id=listing_id,
                title=_card_title(card) or _text(anchor),
                price=_card_text(card, "ad-price"),
                location=_card_text(card, "location-date"),
                url=anchor["href"],
            )
        )
    return listings


def _card_title(card) -> str:
    # The title is the card's heading. Taking it from the heading (rather than
    # an anchor's text) avoids picking up the "PROMOVAT" badge on promoted cards.
    if card is None:
        return ""
    return _text(card.find(["h4", "h5", "h6"]))


def _enclosing_card(anchor):
    for parent in anchor.parents:
        if parent.get("data-cy") == "l-card":
            return parent
    return None


def _card_text(card, testid: str) -> str:
    if card is None:
        return ""
    node = card.find(attrs={"data-testid": testid})
    return _text(node)


def _text(node) -> str:
    return node.get_text(strip=True) if node is not None else ""


def _http_get(url: str):
    """Perform the HTTP GET. Separated so tests can substitute it."""
    return requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)


def fetch_listings(search_url: str) -> list[Listing]:
    """Fetch current listings for a search URL.

    Prefers structured JSON, falls back to HTML parsing. Raises FetchError on a
    network error, non-success status, or an unparseable/empty result rather
    than returning an empty list that could be mistaken for "nothing new".
    """
    try:
        response = _http_get(search_url)
    except Exception as exc:  # network errors, DNS, timeouts, ...
        raise FetchError(f"request to {search_url} failed: {exc}") from exc

    if response.status_code != 200:
        raise FetchError(
            f"unexpected status {response.status_code} for {search_url}"
        )

    body = response.text
    data = _maybe_json(body)
    if isinstance(data, dict) and "data" in data:
        listings = parse_listings_json(data)
    else:
        listings = parse_listings_html(body)

    if not listings:
        raise FetchError(f"no listings parsed from {search_url}")
    return listings


def _maybe_json(body: str):
    try:
        return json.loads(body)
    except ValueError:
        return None
