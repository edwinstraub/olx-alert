## 1. Project setup

- [x] 1.1 Create Python project structure (`olx.py`, `state.py`, `notifier.py`, `main.py`) and a `tests/` directory
- [x] 1.2 Add dependencies (HTTP client, HTML parser, `PyYAML`) via `requirements.txt`/`pyproject.toml`
- [x] 1.3 Add `config.yaml` with `search_url`, `recipient_email`, `max_listings_per_run`
- [x] 1.4 Add `.gitignore` and create the `state/` directory (do not commit secrets)

## 2. Listing fetch (`olx.py`)

- [x] 2.1 Define the `Listing` value object (`id`, `title`, `price`, `location`, `url`, `posted_time`)
- [x] 2.2 Save sample OLX output (JSON and/or HTML) as a test fixture
- [x] 2.3 Write tests: ID extraction from listing URLs, best-effort fields, partial-field handling
- [x] 2.4 Implement JSON parsing of offers into `Listing` objects
- [x] 2.5 Implement HTML fallback parsing of the search page
- [x] 2.6 Implement `fetch_listings(search_url)` preferring JSON, falling back to HTML
- [x] 2.7 Signal fetch failure (network/HTTP error, unparseable body) instead of returning empty

## 3. New-listing detection & state (`state.py`)

- [x] 3.1 Write tests: load/save round-trip, empty when no file, diff logic, bootstrap, cap trimming
- [x] 3.2 Implement `load_seen()` and `save_seen(ids)` over `state/seen.json`
- [x] 3.3 Implement the diff: new = current listings whose ID is not in seen
- [x] 3.4 Implement first-run bootstrap (record all, notify nothing)
- [x] 3.5 Implement the ~1000-ID cap retaining the most recent IDs

## 4. Notification (`notifier.py`)

- [x] 4.1 Define the `Notifier` interface with `send(new_listings)`
- [x] 4.2 Write tests: email subject summarizes count; body lists each listing with link; partial fields render
- [x] 4.3 Implement email subject and body rendering
- [x] 4.4 Implement `EmailNotifier` using Gmail SMTP, reading `SMTP_USER`/`SMTP_PASS` from env and recipient from config
- [x] 4.5 Make the active notifier selectable via config

## 5. Orchestration (`main.py`)

- [x] 5.1 Load `config.yaml`
- [x] 5.2 Fetch listings; guard fetch failure / unexpected empty → log and exit non-zero without advancing state
- [x] 5.3 Load seen state and compute new listings
- [x] 5.4 Bootstrap path on first run (save all, no email)
- [x] 5.5 On new listings: send notification, then save state only after a successful send
- [x] 5.6 Exit codes: success when nothing new or sent; non-zero on fetch/email failure

## 6. Scheduling (`.github/workflows/check.yml`)

- [x] 6.1 Add a cron-scheduled workflow (default every 15 minutes) running `main.py`
- [x] 6.2 Wire `SMTP_USER`/`SMTP_PASS` from GitHub Secrets into the job environment
- [x] 6.3 Commit updated `state/seen.json` back to the repo after a state-changing run

## 7. Documentation & verification

- [x] 7.1 Add a README: configure the search URL, set GitHub Secrets, adjust cron frequency, document scheduling caveat
- [x] 7.2 Run the full test suite and confirm it passes
- [x] 7.3 Document the first-run bootstrap behavior (no email on first run)
