import json

import pytest

import main
import state
from olx import Listing, FetchError


def L(listing_id):
    return Listing(id=listing_id, title=f"bike {listing_id}",
                   url=f"https://www.olx.ro/d/oferta/x-ID{listing_id}.html")


class FakeNotifier:
    def __init__(self, fail=False):
        self.fail = fail
        self.sent = None

    def send(self, new_listings):
        if self.fail:
            raise OSError("smtp down")
        self.sent = list(new_listings)


def cfg(**over):
    base = {"search_url": "https://www.olx.ro/s", "recipient_email": "me@x.com",
            "max_listings_per_run": 20}
    base.update(over)
    return base


def run(config, current, notifier, seen_path, fetch_exc=None):
    def fetch(url):
        if fetch_exc:
            raise fetch_exc
        return current
    return main.run(config, fetch=fetch, notifier=notifier, seen_path=seen_path)


# --- bootstrap ---------------------------------------------------------------

def test_first_run_bootstraps_without_notifying(tmp_path):
    path = tmp_path / "seen.json"
    notifier = FakeNotifier()
    code = run(cfg(), [L("a"), L("b")], notifier, path)
    assert code == 0
    assert notifier.sent is None                    # no email
    assert set(json.loads(path.read_text())) == {"a", "b"}  # all recorded


# --- nothing new -------------------------------------------------------------

def test_no_new_listings_sends_nothing(tmp_path):
    path = tmp_path / "seen.json"
    state.save_seen(["a", "b"], path)
    notifier = FakeNotifier()
    code = run(cfg(), [L("a"), L("b")], notifier, path)
    assert code == 0
    assert notifier.sent is None


# --- new listings ------------------------------------------------------------

def test_new_listings_notify_and_advance_state(tmp_path):
    path = tmp_path / "seen.json"
    state.save_seen(["a"], path)
    notifier = FakeNotifier()
    code = run(cfg(), [L("a"), L("b"), L("c")], notifier, path)
    assert code == 0
    assert [l.id for l in notifier.sent] == ["b", "c"]
    assert set(json.loads(path.read_text())) == {"a", "b", "c"}


def test_max_listings_per_run_caps_notification(tmp_path):
    path = tmp_path / "seen.json"
    state.save_seen(["seed"], path)
    notifier = FakeNotifier()
    current = [L("seed")] + [L(f"n{i}") for i in range(5)]
    code = run(cfg(max_listings_per_run=2), current, notifier, path)
    assert code == 0
    assert len(notifier.sent) == 2                       # capped
    # only the notified ones advance; the rest remain unseen for next run
    assert set(json.loads(path.read_text())) == {"seed", "n0", "n1"}


# --- guards ------------------------------------------------------------------

def test_fetch_failure_does_not_advance_state(tmp_path):
    path = tmp_path / "seen.json"
    state.save_seen(["a"], path)
    notifier = FakeNotifier()
    code = run(cfg(), None, notifier, path, fetch_exc=FetchError("boom"))
    assert code != 0
    assert notifier.sent is None
    assert json.loads(path.read_text()) == ["a"]        # unchanged


def test_unexpected_empty_fetch_is_a_failure(tmp_path):
    path = tmp_path / "seen.json"
    state.save_seen(["a"], path)
    notifier = FakeNotifier()
    code = run(cfg(), [], notifier, path)
    assert code != 0
    assert json.loads(path.read_text()) == ["a"]


def test_send_failure_does_not_advance_state(tmp_path):
    path = tmp_path / "seen.json"
    state.save_seen(["a"], path)
    notifier = FakeNotifier(fail=True)
    code = run(cfg(), [L("a"), L("b")], notifier, path)
    assert code != 0
    assert json.loads(path.read_text()) == ["a"]        # b not added


# --- config loading ----------------------------------------------------------

def test_load_config_reads_yaml(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text("search_url: https://x\nrecipient_email: me@x.com\n"
                 "max_listings_per_run: 5\n")
    config = main.load_config(p)
    assert config["search_url"] == "https://x"
    assert config["max_listings_per_run"] == 5
