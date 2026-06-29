## Context

OLX.ro is a popular Romanian marketplace. Finding a specific motorcycle means
re-running the same filtered search by hand. We want automatic notification
when a new matching listing appears. The source design is approved
(`docs/superpowers/specs/2026-06-29-olx-motorcycle-alert-design.md`); this
document captures the technical decisions for implementation.

Constraints: single personal recipient, no UI, no always-on machine assumed,
read-only access to OLX, and a few minutes of notification delay is acceptable.

## Goals / Non-Goals

**Goals:**
- Notify on new motorcycle listings matching a configurable filter.
- Configurable filter (paste an OLX search URL) and check frequency (cron).
- Email notifications first, behind a pluggable notifier interface.
- Stateless between runs; no database. State lives in the repo.
- Components with single responsibilities, each independently testable (TDD).
- Portable: the same Python can later run under a real cron on a server.

**Non-Goals:**
- Real-time / sub-minute notification.
- A UI or multi-user support.
- Posting, editing, or interacting with OLX listings.

## Decisions

### Runtime: GitHub Actions scheduled workflow
Free, no always-on machine, and the code lives in GitHub anyway. The workflow
runs on cron and commits updated state back to the repo.
- *Alternative — always-on server cron (Hetzner/Coolify):* tighter scheduling
  but requires standing infrastructure. Kept as a documented fallback path; the
  same Python runs there unchanged.
- *Trade-off:* GitHub cron has ~5-minute minimum granularity and may be delayed
  under load. Acceptable here; documented so expectations are correct.

### Data source: OLX public JSON API with HTML fallback
OLX exposes a public JSON offers API used by its own frontend, returning
structured fields without authentication. The user pastes an OLX
search-results URL; each run fetches listings, preferring structured JSON and
falling back to parsing the HTML search page.
- *Why:* keeps the "paste a URL" workflow and degrades gracefully if markup or
  API shape changes.
- *Correctness anchor:* only the stable alphanumeric listing ID (present in
  every listing URL, e.g. `...-IDkAZhr.html`, stored as a string) is required.
  Title/price/location/time are best-effort for rendering the email.

### State: `state/seen.json` committed to the repo
A JSON list of seen IDs, committed by the workflow. No database needed; the job
is stateless between runs.
- *First run is a bootstrap:* record all current IDs as seen without emailing,
  so the user isn't spammed with pre-existing listings.
- *Bounded:* cap to the most recent ~1000 IDs (comfortably above what one
  filtered search returns) so the file never grows unbounded.
- *Alternative — external DB/KV store:* unnecessary complexity for a
  single-user tool; the committed file is simpler and auditable.

### Notifier: pluggable interface, `EmailNotifier` first
`Notifier.send(new_listings)` is the interface; `EmailNotifier` is the first
implementation. Adding Telegram/SMS/WhatsApp later means a new implementation
selected in config — no changes to `olx.py`, `state.py`, or `main.py`.

### Email: Gmail SMTP with an App Password
Free, no third-party service, user already has Gmail; sent via the standard
library `smtplib`. Credentials in GitHub Secrets (`SMTP_USER`, `SMTP_PASS`);
recipient in `config.yaml`.
- *Alternative — transactional email API (SendGrid/SES):* more setup and an
  external account for a single recipient; not worth it now.

### Config / secrets split
Non-secret settings (`search_url`, `recipient_email`, `max_listings_per_run`)
in committed `config.yaml`; secrets only in GitHub Secrets, never committed.

### State advances only after a successful notification
Order within a run: fetch → guard → diff → (bootstrap or notify) → save state →
commit. State advances only after a successful send, so a fetch or email
failure causes a retry next run and nothing is missed.

## Risks / Trade-offs

- **OLX changes its JSON API or HTML markup** → Parser is isolated in `olx.py`
  with tests against saved samples; JSON-with-HTML-fallback reduces single
  points of failure; only the ID is required for correctness.
- **GitHub Actions cron delay/skips under load** → Acceptable per non-goals;
  documented. Fallback to server cron requires no code change.
- **Committing state on every change creates noise / possible race** → Single
  scheduled job, no concurrent runs expected; commits are small and isolated to
  `state/seen.json`.
- **Email send failure loses notification** → State advances only after a
  successful send; failed runs exit non-zero and retry, so listings aren't
  missed. GitHub's failed-workflow notifications surface the problem.
- **Unexpected empty fetch treated as "nothing new"** → Guard treats empty/
  failed fetches as failures (exit non-zero, no state advance) rather than
  silently clearing or skipping.

## Migration Plan

Greenfield project; nothing to migrate. Deployment:
1. Add code, `config.yaml`, and `.github/workflows/check.yml`.
2. Set GitHub Secrets `SMTP_USER` and `SMTP_PASS`.
3. First scheduled run bootstraps state (no email); notifications begin on the
   second run.

Rollback: disable or delete the workflow; the repo and state file are inert
without it.

## Open Questions

- Exact OLX JSON API endpoint/parameters to derive from a pasted search URL —
  to be pinned down against live samples during implementation.
- Default cron cadence (design suggests every 15 minutes) — confirm with the
  user before enabling.
