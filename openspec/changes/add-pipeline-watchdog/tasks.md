## 1. Prerequisites (manual)

- [x] 1.1 Add the `ANTHROPIC_API_KEY` repository secret (Settings → Secrets and variables → Actions)
- [x] 1.2 Confirm the GitHub handle used for @mention/assign → `@edwinstraub`
- [x] 1.3 Confirm the current `anthropics/claude-code-action` version and its inputs against the action's docs
      → `@v1`; inputs `prompt`, `anthropic_api_key`, `claude_args`; headless auto-detected from `workflow_run`

## 2. Workflow scaffold

- [ ] 2.1 Create `.github/workflows/watchdog.yml` with a `workflow_run` trigger on `["OLX motorcycle alert"]`, types `[completed]`
- [ ] 2.2 Gate the job with `if: github.event.workflow_run.conclusion == 'failure'`
- [ ] 2.3 Set job permissions: `actions: read`, `contents: write`, `pull-requests: write`
- [ ] 2.4 Add checkout + Python setup steps and pass `ANTHROPIC_API_KEY` from secrets

## 3. Agent step

- [ ] 3.1 Add the `anthropics/claude-code-action@v1` step with `anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}` and `claude_args: "--model claude-sonnet-4-6 --max-turns 8"`
- [ ] 3.2 Write the `prompt:` input: fetch logs via `gh run view ${{ github.event.workflow_run.id }} --log --log-failed`, read `olx.py`/`main.py`
- [ ] 3.3 Prompt the agent to classify transient vs. real code bug, biasing toward a PR when uncertain
- [ ] 3.4 Prompt: on transient → exit with no PR and no notification
- [ ] 3.5 Prompt: on code bug → make minimal fix on branch `watchdog/fix-<run_id>`, run `pytest`, open a PR
- [ ] 3.6 Prompt: PR body states root cause, change, and honest `pytest` result; flag unverified fixes as needing manual review
- [ ] 3.7 Prompt: @mention and assign the repo owner on the PR; never push to `main` or auto-merge

## 4. Verify behavior

- [ ] 4.1 Lint/validate the workflow YAML (e.g. `actionlint` or a syntax check)
- [ ] 4.2 Trigger a controlled failure of `check.yml` (e.g. temporary bad selector via `workflow_dispatch` on a branch) and confirm the watchdog fires
- [ ] 4.3 Confirm a transient-style failure produces no PR and no notification
- [ ] 4.4 Confirm a code-bug-style failure produces a `watchdog/fix-<run_id>` branch and a PR that @mentions/assigns the owner
- [ ] 4.5 Confirm `main` is never modified directly and no auto-merge occurs

## 5. Documentation

- [ ] 5.1 Add a short "Pipeline watchdog" section to `README.md` (what it does, the `ANTHROPIC_API_KEY` setup step)
