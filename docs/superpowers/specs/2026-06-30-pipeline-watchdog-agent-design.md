# Pipeline Watchdog Agent — Design

**Date:** 2026-06-30
**Status:** Approved for planning

## Problem

The OLX alert pipeline (`.github/workflows/check.yml`, "OLX motorcycle alert")
runs every 4 hours on GitHub Actions. When it fails — most likely because OLX
changed their HTML and broke parsing in `olx.py`, or a dependency/network issue —
nothing happens automatically. The failure can go unnoticed until the user
realizes alerts have stopped arriving.

## Goal

When `check.yml` fails, a separate "watchdog" workflow wakes Claude to:

1. Diagnose the root cause from the failed run's logs.
2. If it's a real code bug, make the minimal fix and verify it with the test suite.
3. Open a pull request with the fix that @mentions and assigns the user.
4. Stop. Nothing reaches `main` without the user's review.

## Decisions (locked)

| Dimension | Decision |
|-----------|----------|
| Autonomy | Propose fix as a **PR**. Never push to `main` directly, never auto-merge. |
| Engine | **`anthropics/claude-code-action@v1`** running in GitHub Actions. |
| Notification | **GitHub @mention + assign** on the PR. No email/Issue channel. |
| Transient failures | **Stay silent** — let the next scheduled run self-heal. No PR, no ping. |
| Verification gate | Run `pytest` before opening a PR; state honestly in the PR body whether it passed. |

## Architecture

One new file: `.github/workflows/watchdog.yml`. No changes to existing app code
or `check.yml`.

### Trigger

```yaml
on:
  workflow_run:
    workflows: ["OLX motorcycle alert"]
    types: [completed]

jobs:
  diagnose:
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
```

- Fires only when the named pipeline completes with `conclusion == 'failure'`.
- The watchdog is a *different* workflow than `check.yml`, so it cannot trigger
  itself into a loop.
- The failed run's ID is available as `github.event.workflow_run.id`.

### Permissions

```yaml
permissions:
  actions: read          # fetch the failed run's logs
  contents: write        # create the fix branch
  pull-requests: write   # open the PR
```

### Secrets

- New repo secret: **`ANTHROPIC_API_KEY`** — used by `claude-code-action`.
  Failure-triggered runs are rare, so API cost is negligible.
- The watchdog does **not** need `SMTP_USER`/`SMTP_PASS` (no email channel).

### Agent step behavior

The step runs `anthropics/claude-code-action@v1` with a prompt instructing Claude to:

1. **Gather context** — fetch logs for the failed run via
   `gh run view ${{ github.event.workflow_run.id }} --log` (and `--log-failed`),
   and read the relevant source (`olx.py`, `main.py`, etc.).
2. **Classify the failure:**
   - **Transient** (network error, timeout, OLX 5xx/rate-limit, DNS) →
     take **no action** and exit. The next scheduled run will self-heal.
   - **Real code bug** (parse error, attribute/None error, dependency/import
     break, config mismatch) → proceed to fix.
3. **Fix** — make the *minimal* change needed to address the root cause.
4. **Verify** — run `pytest`. Capture the result.
5. **Open a PR** on branch `watchdog/fix-<run_id>`:
   - Title: concise root-cause summary.
   - Body: root cause, what changed, and whether `pytest` passed (stated honestly —
     if tests still fail or the fix is uncertain, say so explicitly).
   - **@mention `@edwinstraub` and assign the PR to them.**

### Loop / noise prevention

- Watchdog only triggers on `check.yml` failure, never on its own runs.
- Transient failures produce no PR and no notification, so a flaky network does
  not spam the user every 4 hours.
- One PR per failed run (branch keyed by `run_id`), so repeated identical failures
  create distinct, traceable PRs rather than silently piling onto one branch.

## Verification gate detail

The agent must run the existing `pytest` suite before opening a PR. The PR body
reports the outcome truthfully:

- Tests pass → "Verified: `pytest` green."
- Tests fail or no coverage for the fixed path → say so, and label the PR as
  needing manual verification. A best-effort PR that says "I think this is the
  cause but couldn't fully verify" is acceptable and explicitly desired over no PR.

`check.yml` itself is **not** re-run by the watchdog (it requires SMTP secrets and
commits live state). `pytest` is the verification surface.

## Explicitly out of scope (YAGNI)

- Auto-merge or direct pushes to `main`.
- Email or GitHub-Issue notification channels.
- Re-running the full `check.yml` pipeline.
- Retry/backoff logic for transient failures (the existing 4-hour schedule covers it).
- Fixing failures in any workflow other than "OLX motorcycle alert".

## Files touched

| File | Change |
|------|--------|
| `.github/workflows/watchdog.yml` | **New.** The entire feature. |
| Repo secrets | Add `ANTHROPIC_API_KEY` (manual, by the user). |

## Open risks / notes

- `claude-code-action@v1` API surface (inputs, default model, PR-creation
  capability) should be confirmed against current docs during implementation; the
  prompt may need tuning so the agent reliably opens the PR rather than only
  commenting.
- The user must add the `ANTHROPIC_API_KEY` secret before the watchdog can work;
  the implementation plan should call this out as a manual setup step.
