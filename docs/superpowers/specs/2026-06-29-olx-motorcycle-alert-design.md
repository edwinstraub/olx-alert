# OLX.ro Motorcycle Listing Alert — Design

**Date:** 2026-06-29
**Status:** Approved (design), pending implementation plan

## Goal

Get notified when new motorcycle listings matching a configurable filter
appear on [olx.ro](https://www.olx.ro). The filter and the check frequency are
configurable. Notifications start over email, with the design kept pluggable so
SMS / WhatsApp / Telegram can be added later without rework.

## Non-goals

- Real-time (sub-minute) notification. Marketplace monitoring tolerates a few
  minutes of delay.
- A UI. Configuration is a file in the repo.
- Multi-user support. This is a personal tool for a single recipient.
- Posting, editing, or interacting with OLX listings — read-only monitoring.

## Runtime & deployment

- **Where:** GitHub Actions, scheduled (cron) workflow. Free, no always-on
  machine required, and the code lives in GitHub where the user wants it anyway.
- **Fallback path:** the same Python code can later run on the user's
  Hetzner/Coolify server under a real cron if GitHub Actions timing or
  reliability proves insufficient. No code changes required for that move.
- **Scheduling caveat:** GitHub Actions scheduled jobs have ~5-minute minimum
  granularity and may be delayed several minutes under load. Acceptable for this
  use case; documented so expectations are correct.

## Data source

OLX.ro exposes a public JSON API used by its own frontend:

```
https://www.olx.ro/api/v1/offers/?...
```

It returns structured offers without authentication: `id`, `title`, `url`,
`created_time`, `price` (value/currency/negotiable), `location.city.name`,
`location.region.name`, `params` (year, mileage, engine, etc.).

### Fetch strategy (hybrid)

The user configures the filter by **pasting an OLX.ro search-results URL** (built
using OLX's own filter UI: motorcycle subcategory, hometown, price range,
keywords — anything OLX supports).

On each run the app fetches the listings for that filter and prefers structured
JSON data when available, falling back to parsing the HTML search page. The only
field required for correctness is each listing's **stable numeric ID** (present
in every listing URL, e.g. `.../d/oferta/...-ID<digits>.html`). Title, price,
location, and posted time are best-effort and used only to render the email; if
any are missing the notification still sends with whatever is available.

This keeps the "paste a URL" workflow, depends only on the stable ID for
correctness, and degrades gracefully if OLX changes its markup.

## Components

Each unit has one purpose, a clear interface, and is independently testable.

| File | Responsibility | Interface (conceptual) |
|------|----------------|------------------------|
| `config.yaml` | User settings (non-secret) | `search_url`, `recipient_email`, `max_listings_per_run` |
| `olx.py` | Fetch + parse listings for a search URL | `fetch_listings(search_url) -> list[Listing]` |
| `state.py` | Persist the set of seen listing IDs | `load_seen() -> set[int]`, `save_seen(ids)` |
| `notifier.py` | Send notifications; pluggable channels | `Notifier.send(new_listings)`; `EmailNotifier` impl |
| `main.py` | Orchestrate one run | entrypoint |
| `.github/workflows/check.yml` | Schedule, run, commit state | cron + job |

`Listing` is a simple value object: `{ id: int, title: str, price: str,
location: str, url: str, posted_time: str }`.

`Notifier` is a base interface (`send(new_listings)`); `EmailNotifier` is the
first implementation. Adding Telegram/SMS/WhatsApp later means adding a new
implementation and selecting it in config — no changes to `olx.py`, `state.py`,
or `main.py`.

## Data flow (one run)

1. Load `config.yaml`.
2. `fetch_listings(search_url)` → current listings.
3. Guard: if fetch failed or returned 0 listings unexpectedly → log, exit
   non-zero, **do not update state**.
4. `load_seen()` → previously seen IDs.
5. Compute `new = [l for l in current if l.id not in seen]`.
6. If first run (no prior state): **bootstrap** — save all current IDs as seen,
   send no email. Exit success.
7. Else if `new` is non-empty: `notifier.send(new)`.
8. Only after a successful send: add new IDs to seen and `save_seen(...)`.
9. Workflow commits the updated `state/seen.json` back to the repo.

## New-listing detection & state

- State is `state/seen.json`: a list of listing IDs, committed to the repo so it
  persists across runs (no database needed).
- **First run is a bootstrap**: all currently-visible listings are recorded as
  seen *without* emailing, so the user is not spammed with every pre-existing
  listing. Real notifications begin on the second run.
- State is capped to the most recent ~1000 IDs so the file never grows
  unbounded. (Cap chosen comfortably above the number of listings a single
  filtered search returns.)

## Scheduling / frequency

- Defined by the `cron` expression in `.github/workflows/check.yml` and is the
  single place to change check frequency.
- Default suggestion: every 15 minutes (`*/15 * * * *`), adjustable.

## Email delivery

- **Gmail SMTP with an App Password** — free, no third-party service, user
  already has Gmail.
- Credentials in **GitHub Secrets**: `SMTP_USER`, `SMTP_PASS`. Recipient address
  in `config.yaml` (non-secret).
- Email content: subject summarizing count (e.g. `🏍️ 2 new motorcycle listings
  on OLX`); body lists each new listing with title, price, location, posted
  time, and a direct link.

## Configuration & secrets split

- **Non-secret** (`config.yaml`, committed): `search_url`, `recipient_email`,
  `max_listings_per_run`.
- **Secret** (GitHub Secrets, never committed): `SMTP_USER`, `SMTP_PASS`.

## Error handling

- **Fetch failure or unexpected empty result:** log the error, exit non-zero,
  and do not advance state. GitHub's failed-workflow notifications surface the
  problem; listings are retried on the next run, so nothing is missed.
- **Email failure:** do not advance state; fail the run so the same new listings
  are retried next run. State only advances after a *successful* notification.
- **Partial parse:** missing optional fields (price/location/time) do not block
  a notification; the email renders with whatever is available.

## Testing (TDD)

- `olx.py` parser: against a saved sample of OLX output (JSON and/or HTML),
  asserts correct extraction of IDs and best-effort fields.
- Diff logic: given seen IDs and current listings, returns the correct new set;
  bootstrap path emits nothing.
- Email formatting: renders expected subject/body from a set of listings without
  actually sending.

## Future extensions

- Additional notifier implementations (Telegram, SMS via Twilio, WhatsApp).
- Multiple saved filters / searches.
- Migration to Hetzner/Coolify cron container for tighter scheduling.
