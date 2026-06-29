## Why

Finding a specific motorcycle on OLX.ro means repeatedly re-running the same
filtered search by hand and hoping to catch a new listing before someone else
does. We want to be notified automatically when a new listing matching a
configurable filter appears, so no manual polling is needed and good listings
aren't missed.

## What Changes

- Add a scheduled job that periodically fetches OLX.ro listings for a
  user-defined search filter (pasted as an OLX search-results URL).
- Detect listings not seen on prior runs and send a notification for them.
- Send notifications by email first (Gmail SMTP + App Password), behind a
  pluggable notifier interface so Telegram/SMS/WhatsApp can be added later.
- Persist the set of seen listing IDs in the repo (`state/seen.json`) so the
  job is stateless between runs and needs no database.
- Bootstrap on first run: record all current listings as seen without
  emailing, so the user isn't spammed with pre-existing listings.
- Run on GitHub Actions on a cron schedule; the workflow commits updated state
  back to the repo.
- Keep configuration (search URL, recipient, caps) in a committed
  `config.yaml`; keep SMTP credentials in GitHub Secrets.

## Capabilities

### New Capabilities
- `listing-fetch`: Fetch and parse motorcycle listings for an OLX.ro search
  URL into normalized `Listing` value objects, preferring structured JSON and
  degrading gracefully to HTML parsing; correctness depends only on the stable
  alphanumeric listing ID (stored as a string).
- `new-listing-detection`: Persist seen listing IDs and compute the set of new
  listings each run, including the first-run bootstrap and a bounded state cap.
- `notification`: Deliver new-listing notifications through a pluggable
  `Notifier` interface, with an `EmailNotifier` (Gmail SMTP) as the first
  implementation; state only advances after a successful send.
- `scheduled-runner`: Orchestrate one run end-to-end on a cron schedule via
  GitHub Actions, including config loading, error/guard handling, and commit of
  updated state.

### Modified Capabilities
<!-- None — this is a greenfield project with no existing specs. -->

## Impact

- New Python project: `olx.py`, `state.py`, `notifier.py`, `main.py`,
  `config.yaml`, `state/seen.json`.
- New GitHub Actions workflow: `.github/workflows/check.yml` (cron schedule,
  run, commit state).
- New dependencies: an HTTP client and HTML parser (e.g. `requests` +
  `beautifulsoup4`), `PyYAML` for config; email via the Python standard
  library (`smtplib`).
- New GitHub Secrets required: `SMTP_USER`, `SMTP_PASS`.
- No existing code or systems are modified or removed.
