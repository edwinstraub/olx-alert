## Why

The OLX alert pipeline (`.github/workflows/check.yml`) runs unattended every 4
hours. When it fails — most likely because OLX changed their HTML and broke
parsing in `olx.py` — nothing happens, and the failure can go unnoticed until the
user realizes alerts have stopped arriving. We want a watchdog that catches
failures, attempts a fix, and pulls the user in only when their review is needed.

## What Changes

- Add a new `.github/workflows/watchdog.yml` workflow that triggers when the
  "OLX motorcycle alert" workflow completes with a failure.
- On failure, the workflow runs Claude (`anthropics/claude-code-action`) to fetch
  the failed run's logs, diagnose the root cause, and classify the failure.
- For transient failures (network/timeout/OLX 5xx), the watchdog stays silent and
  lets the next scheduled run self-heal — no PR, no notification.
- For real code bugs, the agent makes the minimal fix, runs `pytest` to verify,
  and opens a pull request on a `watchdog/fix-<run_id>` branch.
- The PR @mentions and assigns the user so they are notified via GitHub. Nothing
  is pushed to `main` or auto-merged.
- A new `ANTHROPIC_API_KEY` repository secret is required (manual setup step).

## Capabilities

### New Capabilities
- `pipeline-watchdog`: Detect failures of the OLX alert pipeline, diagnose the
  root cause from logs, attempt a verified minimal fix, and surface it to the user
  as a review-only pull request — while staying silent on transient failures.

### Modified Capabilities
<!-- None. No existing spec-level behavior changes; check.yml and app code are untouched. -->

## Impact

- **New file:** `.github/workflows/watchdog.yml` — the entire feature.
- **No changes** to existing app code (`olx.py`, `main.py`, etc.) or to
  `check.yml`.
- **New repo secret:** `ANTHROPIC_API_KEY` (added manually by the user).
- **New external dependency:** `anthropics/claude-code-action` GitHub Action and
  Anthropic API usage (negligible cost — only runs on rare pipeline failures).
- **GitHub permissions** used by the new workflow: `actions: read`,
  `contents: write`, `pull-requests: write`.
