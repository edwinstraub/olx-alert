"""Persist and diff the set of seen listing IDs.

State lives in ``state/seen.json`` as a JSON list of string IDs, ordered oldest
to newest, committed to the repo so it survives across runs. The list is capped
to the most recent ``DEFAULT_CAP`` IDs so it never grows unbounded.

(The ``state.py`` module and the ``state/`` data directory coexist: a regular
module takes import precedence over the directory's namespace package.)
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_CAP = 1000
DEFAULT_PATH = Path("state") / "seen.json"


def load_seen(path: Path | str = DEFAULT_PATH) -> set[str]:
    """Return the set of seen IDs, or an empty set when no state exists."""
    p = Path(path)
    if not p.exists():
        return set()
    return set(json.loads(p.read_text(encoding="utf-8")))


def load_seen_list(path: Path | str = DEFAULT_PATH) -> list[str]:
    """Return seen IDs as an ordered list (oldest-to-newest), [] when absent."""
    p = Path(path)
    if not p.exists():
        return []
    return list(json.loads(p.read_text(encoding="utf-8")))


def save_seen(ids, path: Path | str = DEFAULT_PATH, cap: int = DEFAULT_CAP) -> None:
    """Persist ``ids`` (oldest-to-newest order) to ``path``, capped to ``cap``.

    Duplicates are removed preserving first-seen order; when the list exceeds
    ``cap`` the oldest entries are dropped, keeping the most recent IDs.
    """
    ordered = list(dict.fromkeys(str(i) for i in ids))
    if len(ordered) > cap:
        ordered = ordered[-cap:]
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(ordered), encoding="utf-8")


def new_listings(current, seen: set[str]):
    """Return the listings in ``current`` whose ID is not in ``seen``."""
    return [listing for listing in current if listing.id not in seen]


def is_first_run(seen: set[str]) -> bool:
    """True when there is no prior state (the bootstrap run)."""
    return not seen


def ids(listings) -> list[str]:
    """Return the IDs of ``listings`` in order."""
    return [listing.id for listing in listings]
