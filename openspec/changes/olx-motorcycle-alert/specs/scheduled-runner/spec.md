## ADDED Requirements

### Requirement: Configuration loading

The system SHALL load non-secret settings from a committed `config.yaml`
providing at least `search_url`, `recipient_email`, and
`max_listings_per_run`. Secrets (`SMTP_USER`, `SMTP_PASS`) SHALL come from the
environment, never from `config.yaml`.

#### Scenario: Load config at start of run
- **WHEN** a run starts
- **THEN** the orchestrator reads `search_url`, `recipient_email`, and `max_listings_per_run` from `config.yaml`

#### Scenario: Secrets are not in config
- **WHEN** the run needs SMTP credentials
- **THEN** they are read from the environment and are absent from `config.yaml`

### Requirement: Single-run orchestration

The system SHALL provide a `main.py` entrypoint that orchestrates one run: load
config, fetch listings, load seen state, compute new listings, notify when
appropriate, and advance state only after a successful notification.

#### Scenario: New listings present
- **WHEN** a non-first run finds new listings
- **THEN** the orchestrator sends a notification and, on success, saves the updated seen state

#### Scenario: No new listings
- **WHEN** a non-first run finds no new listings
- **THEN** no notification is sent and the run exits successfully

### Requirement: Guard against bad fetches

The system SHALL NOT advance state on a fetch failure or an unexpected empty
result. In those cases it SHALL log the problem and exit non-zero so the run is
marked failed and retried next run.

#### Scenario: Fetch fails
- **WHEN** fetching listings fails or returns an unexpected empty result
- **THEN** the orchestrator logs the error, does not update state, and exits non-zero

### Requirement: Scheduled execution via GitHub Actions

The system SHALL run on a cron schedule defined in
`.github/workflows/check.yml`, which SHALL be the single place to change check
frequency (default suggestion: every 15 minutes). After a successful run that
changes state, the workflow SHALL commit the updated `state/seen.json` back to
the repository.

#### Scenario: Scheduled run commits updated state
- **WHEN** the scheduled workflow runs and the seen state changes
- **THEN** the workflow commits the updated `state/seen.json` back to the repository

#### Scenario: Frequency is configured in one place
- **WHEN** the check frequency needs to change
- **THEN** it is changed by editing the `cron` expression in `.github/workflows/check.yml`
