import json

import state
from olx import Listing


def L(listing_id):
    return Listing(id=listing_id)


# --- load / save round-trip --------------------------------------------------

def test_load_returns_empty_set_when_no_file(tmp_path):
    assert state.load_seen(tmp_path / "seen.json") == set()


def test_save_then_load_round_trip(tmp_path):
    path = tmp_path / "seen.json"
    state.save_seen(["kHuzM", "kAZhr"], path)
    assert state.load_seen(path) == {"kHuzM", "kAZhr"}


def test_save_writes_a_json_list(tmp_path):
    path = tmp_path / "seen.json"
    state.save_seen(["kHuzM", "kAZhr"], path)
    assert json.loads(path.read_text()) == ["kHuzM", "kAZhr"]


def test_save_deduplicates_preserving_order(tmp_path):
    path = tmp_path / "seen.json"
    state.save_seen(["a", "b", "a", "c"], path)
    assert json.loads(path.read_text()) == ["a", "b", "c"]


def test_load_seen_list_preserves_order(tmp_path):
    path = tmp_path / "seen.json"
    state.save_seen(["a", "b", "c"], path)
    assert state.load_seen_list(path) == ["a", "b", "c"]


def test_load_seen_list_empty_when_no_file(tmp_path):
    assert state.load_seen_list(tmp_path / "seen.json") == []


# --- diff --------------------------------------------------------------------

def test_new_listings_returns_only_unseen():
    current = [L("a"), L("b"), L("c")]
    seen = {"b"}
    assert [l.id for l in state.new_listings(current, seen)] == ["a", "c"]


def test_new_listings_empty_when_all_seen():
    current = [L("a"), L("b")]
    assert state.new_listings(current, {"a", "b"}) == []


# --- bootstrap ---------------------------------------------------------------

def test_is_first_run_true_when_no_state():
    assert state.is_first_run(set()) is True


def test_is_first_run_false_when_state_exists():
    assert state.is_first_run({"a"}) is False


# --- cap ---------------------------------------------------------------------

def test_cap_keeps_most_recent(tmp_path):
    path = tmp_path / "seen.json"
    ids = [str(i) for i in range(1500)]  # oldest -> newest
    state.save_seen(ids, path, cap=1000)
    stored = json.loads(path.read_text())
    assert len(stored) == 1000
    assert stored[0] == "500"      # oldest 500 trimmed
    assert stored[-1] == "1499"    # newest retained
