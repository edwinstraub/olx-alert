import json
from pathlib import Path

import pytest

import olx
from olx import Listing, FetchError

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


# --- ID extraction -----------------------------------------------------------

def test_extract_id_from_relative_url():
    url = "/d/oferta/honda-cbr-600rr-IDkHuzM.html"
    assert olx.extract_id(url) == "kHuzM"


def test_extract_id_from_absolute_url():
    url = "https://www.olx.ro/d/oferta/ktm-duke-125-motocicleta-a1-IDkAZhr.html"
    assert olx.extract_id(url) == "kAZhr"


def test_extract_id_returns_none_when_absent():
    assert olx.extract_id("https://www.olx.ro/some/other/page") is None


# --- JSON parsing ------------------------------------------------------------

def test_parse_json_extracts_all_listings():
    data = json.loads(load("offers.json"))
    listings = olx.parse_listings_json(data)
    assert len(listings) == 3
    assert all(isinstance(l, Listing) for l in listings)


def test_parse_json_extracts_id_from_url():
    data = json.loads(load("offers.json"))
    ids = [l.id for l in olx.parse_listings_json(data)]
    assert ids == ["kHuzM", "kAZhr", "kFr25"]


def test_parse_json_extracts_best_effort_fields():
    data = json.loads(load("offers.json"))
    first = olx.parse_listings_json(data)[0]
    assert first.title == "Honda CBR 600RR"
    assert first.price == "5 500 €"
    assert "Cluj-Napoca" in first.location
    assert first.posted_time == "2026-06-29T10:15:00+03:00"
    assert first.url.endswith("honda-cbr-600rr-IDkHuzM.html")


def test_parse_json_tolerates_missing_optional_fields():
    data = json.loads(load("offers.json"))
    third = olx.parse_listings_json(data)[2]  # no price/location/time params
    assert third.id == "kFr25"
    assert third.price == ""
    assert third.location == ""
    assert third.posted_time == ""


# --- HTML parsing ------------------------------------------------------------

def test_parse_html_extracts_all_listings():
    listings = olx.parse_listings_html(load("search.html"))
    assert len(listings) == 3


def test_parse_html_extracts_ids():
    listings = olx.parse_listings_html(load("search.html"))
    assert [l.id for l in listings] == ["kHuzM", "kAZhr", "kFr25"]


def test_parse_html_extracts_best_effort_fields():
    listings = olx.parse_listings_html(load("search.html"))
    first = listings[0]
    assert first.title == "Honda CBR 600RR"
    assert first.price == "5 500 €"
    assert "Cluj-Napoca" in first.location


def test_parse_html_title_ignores_promoted_badge():
    # The first card is "promoted": a PROMOVAT badge anchor precedes the title.
    # The title must come from the heading, not the badge.
    first = olx.parse_listings_html(load("search.html"))[0]
    assert first.title == "Honda CBR 600RR"
    assert "PROMOVAT" not in first.title


def test_parse_html_tolerates_missing_fields():
    listings = olx.parse_listings_html(load("search.html"))
    third = listings[2]  # card with no price/location
    assert third.id == "kFr25"
    assert third.price == ""


def test_parse_html_deduplicates_by_id():
    html = (
        '<a href="/d/oferta/a-IDkHuzM.html">A</a>'
        '<a href="/d/oferta/a-IDkHuzM.html">A again</a>'
    )
    listings = olx.parse_listings_html(html)
    assert [l.id for l in listings] == ["kHuzM"]


# --- fetch_listings dispatch + failure ---------------------------------------

def test_fetch_prefers_json(monkeypatch):
    body = load("offers.json")

    def fake_get(url):
        return _Resp(200, body, "application/json")

    monkeypatch.setattr(olx, "_http_get", fake_get)
    listings = olx.fetch_listings("https://www.olx.ro/whatever")
    assert [l.id for l in listings] == ["kHuzM", "kAZhr", "kFr25"]


def test_fetch_falls_back_to_html(monkeypatch):
    body = load("search.html")

    def fake_get(url):
        return _Resp(200, body, "text/html")

    monkeypatch.setattr(olx, "_http_get", fake_get)
    listings = olx.fetch_listings("https://www.olx.ro/whatever")
    assert [l.id for l in listings] == ["kHuzM", "kAZhr", "kFr25"]


def test_fetch_raises_on_http_error(monkeypatch):
    def fake_get(url):
        return _Resp(503, "Service Unavailable", "text/html")

    monkeypatch.setattr(olx, "_http_get", fake_get)
    with pytest.raises(FetchError):
        olx.fetch_listings("https://www.olx.ro/whatever")


def test_fetch_raises_on_unparseable_body(monkeypatch):
    def fake_get(url):
        return _Resp(200, "<html>no listings here</html>", "text/html")

    monkeypatch.setattr(olx, "_http_get", fake_get)
    with pytest.raises(FetchError):
        olx.fetch_listings("https://www.olx.ro/whatever")


def test_fetch_raises_on_network_error(monkeypatch):
    def fake_get(url):
        raise OSError("connection refused")

    monkeypatch.setattr(olx, "_http_get", fake_get)
    with pytest.raises(FetchError):
        olx.fetch_listings("https://www.olx.ro/whatever")


class _Resp:
    """Minimal stand-in for a requests.Response."""

    def __init__(self, status_code, text, content_type):
        self.status_code = status_code
        self.text = text
        self.headers = {"Content-Type": content_type}
