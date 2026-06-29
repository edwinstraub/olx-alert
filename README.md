# OLX.ro Motorcycle Listing Alert

Get an email when a new motorcycle listing matching your filter appears on
[olx.ro](https://www.olx.ro). Runs for free on GitHub Actions on a schedule;
notification channels are pluggable (email first, Telegram/SMS/WhatsApp later).

## How it works

On each scheduled run the app fetches the listings for your saved OLX search,
compares them against the IDs it has already seen (`state/seen.json`, committed
to the repo), and emails you any new ones. State only advances after a
successful email, so nothing is missed if a run fails.

| File | Responsibility |
|------|----------------|
| `config.yaml` | Non-secret settings (search URL, recipient, caps) |
| `olx.py` | Fetch + parse listings for a search URL |
| `state.py` | Persist and diff the set of seen listing IDs |
| `notifier.py` | Pluggable notifications; `EmailNotifier` (Gmail SMTP) |
| `main.py` | Orchestrate one run |
| `.github/workflows/check.yml` | Schedule, run, commit state |

## Setup

### 1. Configure your search filter

Open OLX.ro, use its filter UI to build the search you want (motorcycle
subcategory, town, price range, keywords — anything OLX supports), then copy the
resulting search-results URL from your browser. Paste it into `config.yaml`:

```yaml
search_url: "https://www.olx.ro/...your filtered search..."
recipient_email: "you@example.com"
max_listings_per_run: 20
notifier: email
```

### 2. Create a Gmail App Password

Email is sent via Gmail SMTP. With 2-Step Verification enabled on your Google
account, create an **App Password** (Google Account → Security → App passwords).
This is a 16-character password used only by this app.

### 3. Add GitHub Secrets

In your repository: **Settings → Secrets and variables → Actions → New
repository secret**. Add:

| Secret | Value |
|--------|-------|
| `SMTP_USER` | Your Gmail address (e.g. `you@gmail.com`) |
| `SMTP_PASS` | The 16-character Gmail App Password |

These are never committed; the recipient address lives in `config.yaml`.

### 4. Enable the workflow

The workflow in `.github/workflows/check.yml` runs automatically once pushed.
You can also trigger it manually from the **Actions** tab ("Run workflow").

## First run is a bootstrap (no email)

**The first run does not email you.** It records every currently-visible listing
as "seen" so you aren't spammed with the entire back-catalogue of existing
listings. Real notifications begin on the **second** run, for listings that
appear after the bootstrap. This is by design.

## Changing the check frequency

Frequency is controlled in exactly one place — the `cron` expression in
`.github/workflows/check.yml`:

```yaml
- cron: "*/15 * * * *"   # every 15 minutes (default)
```

**Scheduling caveat:** GitHub Actions scheduled jobs have a ~5-minute minimum
granularity and may be delayed several minutes under load. That's fine for
marketplace polling, but don't expect to-the-second timing. If you ever need
tighter scheduling, the same Python can run under a real cron on your own server
with no code changes.

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

To run a real check locally (will send email if there are new listings):

```bash
export SMTP_USER="you@gmail.com"
export SMTP_PASS="your-app-password"
python main.py
```

## Tests

The suite (`pytest`) covers parsing (JSON + HTML fallback, ID extraction,
partial fields, fetch-failure signaling), state (load/save, diff, bootstrap
detection, the ~1000-ID cap), email rendering, and run orchestration (bootstrap,
no-new, new-with-advance, per-run cap, and the fetch/send failure guards) — all
without network or sending real email.

> **Note on parser fixtures:** the fixtures in `tests/fixtures/` are
> representative of OLX's structure (the alphanumeric `-ID<…>.html` listing-URL
> format is confirmed against live OLX). If OLX changes its markup or JSON shape,
> refresh the fixtures from a live sample and the parser tests will guide the fix.
