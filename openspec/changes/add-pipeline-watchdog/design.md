## Context

The OLX alert pipeline (`.github/workflows/check.yml`, "OLX motorcycle alert")
polls OLX every 4 hours and emails new listings. Its most fragile surface is HTML
parsing in `olx.py` — when OLX changes markup, parsing breaks and alerts silently
stop. The repo already has a `pytest` suite. There is no automated reaction to a
failed run today.

This design adds a watchdog workflow that reacts to pipeline failures by running
Claude to diagnose and propose a fix. The full motivation is in `proposal.md`; the
required behaviors are in `specs/pipeline-watchdog/spec.md`.

## Goals / Non-Goals

**Goals:**
- React automatically when `check.yml` fails.
- Diagnose root cause from the failed run's logs.
- Propose a verified, minimal fix as a review-only PR that notifies the user.
- Avoid notification noise on transient failures.

**Non-Goals:**
- Auto-merging or pushing fixes to `main`.
- Email or GitHub-Issue notification channels.
- Re-running the full `check.yml` pipeline (needs SMTP secrets and mutates state).
- Retry/backoff for transient failures — the 4-hour schedule covers recovery.
- Watching any workflow other than "OLX motorcycle alert".

## Decisions

**Trigger: `workflow_run` on the named workflow, gated to `failure`.**
The job uses `if: github.event.workflow_run.conclusion == 'failure'`. The run ID
is read from `github.event.workflow_run.id`.
- *Alternative considered:* a step appended to `check.yml` that runs on failure.
  Rejected — it would couple watchdog logic into the pipeline and run in the same
  job context. A separate `workflow_run`-triggered workflow is cleanly isolated and
  cannot self-trigger (it watches `check.yml`, not itself).

**Engine: `anthropics/claude-code-action@v1`.**
Runs Claude inside the workflow with built-in tool access to read logs (`gh run
view`), edit files, run `pytest`, and open a PR. Needs an `ANTHROPIC_API_KEY` repo
secret. Confirmed current input surface (v1 GA):
- `prompt:` — the fixed instruction (beta's `direct_prompt`, now renamed).
- `anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}` — the API key.
- `claude_args:` — model/turn/tool flags, e.g.
  `--model claude-sonnet-4-6 --max-turns 8`.
- Headless mode is **auto-detected** from the trigger event — a `workflow_run`
  trigger plus a fixed `prompt` runs without any `mode:` input (removed in v1).
- *Alternative considered:* an out-of-repo scheduled cloud agent polling for failed
  runs. Rejected — more moving parts and latency; in-CI is simpler and event-driven.

**Model: `claude-sonnet-4-6` via `claude_args`.**
Sonnet is the cost-appropriate default for log triage + a minimal scraper fix.
Passed as `--model claude-sonnet-4-6`; can be raised to Opus later if fixes prove
too hard for Sonnet.

**Autonomy: review-only PR.**
The agent commits to `watchdog/fix-<run_id>` and opens a PR; never touches `main`,
never auto-merges. A scraper "fix" can be wrong, so a human gate is required.

**Verification gate: `pytest` before PR, honest reporting.**
The agent runs `pytest` and states the result in the PR body. A best-effort PR
labeled "unverified — needs manual review" is preferred over no PR when the fix is
uncertain. `check.yml` is not re-run because it needs SMTP secrets and commits live
state.

**Notification: GitHub @mention + assign.**
The PR @mentions and assigns the repo owner; GitHub's native email/web notification
does the rest. No separate channel is built.

**Transient failures: silent.**
On network/timeout/5xx/DNS classification the agent exits with no PR and no ping,
so a flaky network does not spam the user every 4 hours.

**Branch keyed by run ID.**
`watchdog/fix-<run_id>` gives one traceable PR per failed run rather than piling
onto a shared branch.

## Risks / Trade-offs

- **Agent misclassifies a real bug as transient** → stays silent, alerts keep
  failing unnoticed. Mitigation: classification prompt biases toward opening a PR
  when uncertain; only clear network/5xx/DNS signals count as transient.
- **Agent opens a PR with a wrong or non-functional fix** → review-only gate means
  no `main` impact; honest `pytest` reporting flags low-confidence fixes for the user.
- **`claude-code-action` API surface (inputs, default model, PR-creation) differs
  from assumptions** → confirm against current action docs during implementation;
  tune the prompt so the agent reliably opens a PR rather than only commenting.
- **Repeated identical failures create multiple PRs** → acceptable; per-run branches
  keep them distinct and traceable, and the user can close duplicates.
- **Cost of API calls** → negligible; runs only on rare failures.

## Migration Plan

1. Add the `ANTHROPIC_API_KEY` repository secret (manual, by the user).
2. Merge `.github/workflows/watchdog.yml`.
3. The watchdog activates automatically on the next failed pipeline run.

**Rollback:** delete `watchdog.yml` (and optionally the secret). No app code or
`check.yml` change is involved, so rollback is isolated and safe.

## Open Questions

- None — all resolved (see below).

## Resolved

- **GitHub handle (was open):** `@edwinstraub`, confirmed by the user. Used for
  the PR @mention and assignment.

- **Action version/inputs (was open):** `@v1` GA. Inputs are `prompt`,
  `anthropic_api_key`, `claude_args`; headless mode is auto-detected from the
  `workflow_run` trigger (no `mode:` input). The action can open the PR itself, so
  no separate `gh pr create` step is required. The `ANTHROPIC_API_KEY` secret has
  been created in the repository.
- **Gate (clarification):** use
  `if: github.event.workflow_run.conclusion == 'failure'`, **not** `if: failure()` —
  `failure()` reflects the watchdog job's own prior steps, not the upstream pipeline.
