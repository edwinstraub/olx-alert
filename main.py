"""Orchestrate one run of the OLX motorcycle alert.

Run order (state advances only after a successful notification):

1. Load config.
2. Fetch listings; guard fetch failure / unexpected empty -> exit non-zero,
   do not advance state.
3. Load seen state; on first run, bootstrap (record all, send nothing).
4. Compute new listings; if none, exit 0.
5. Notify (capped to ``max_listings_per_run``); only on success advance state.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import yaml

import olx
import state
from notifier import get_notifier

log = logging.getLogger("olx_alert")

CONFIG_PATH = Path("config.yaml")


def load_config(path: Path | str = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def run(config, *, fetch=olx.fetch_listings, notifier=None,
        seen_path=state.DEFAULT_PATH) -> int:
    """Execute one run. Returns a process exit code (0 success, non-zero fail)."""
    # 2. Fetch + guard.
    try:
        current = fetch(config["search_url"])
    except olx.FetchError as exc:
        log.error("fetch failed; state not advanced: %s", exc)
        return 1
    if not current:
        log.error("fetch returned no listings unexpectedly; state not advanced")
        return 1

    # 3. Bootstrap on first run.
    seen = state.load_seen(seen_path)
    if state.is_first_run(seen):
        state.save_seen(state.ids(current), seen_path)
        log.info("bootstrap: recorded %d listings, no email sent", len(current))
        return 0

    # 4. Diff.
    new = state.new_listings(current, seen)
    if not new:
        log.info("no new listings")
        return 0

    cap = config.get("max_listings_per_run")
    if cap:
        new = new[:cap]

    # 5. Notify, then advance state only on success.
    try:
        notifier.send(new)
    except Exception as exc:  # noqa: BLE001 - any send failure must not advance state
        log.error("notification failed; state not advanced: %s", exc)
        return 1

    previous = state.load_seen_list(seen_path)
    state.save_seen(previous + state.ids(new), seen_path)
    log.info("notified %d new listings; state advanced", len(new))
    return 0


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_config()
    notifier = get_notifier(config)
    return run(config, notifier=notifier)


if __name__ == "__main__":
    sys.exit(main())
