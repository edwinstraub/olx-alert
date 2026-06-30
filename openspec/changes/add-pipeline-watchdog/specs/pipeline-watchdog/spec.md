## ADDED Requirements

### Requirement: Trigger only on pipeline failure

The watchdog workflow SHALL run only when the "OLX motorcycle alert" workflow
(`check.yml`) completes with a `failure` conclusion, and SHALL NOT trigger on its
own runs or on successful pipeline runs.

#### Scenario: Pipeline fails

- **WHEN** the "OLX motorcycle alert" workflow completes with conclusion `failure`
- **THEN** the watchdog workflow starts and has access to the failed run's ID

#### Scenario: Pipeline succeeds

- **WHEN** the "OLX motorcycle alert" workflow completes with conclusion `success`
- **THEN** the watchdog workflow does not perform any diagnosis or fix work

#### Scenario: No self-triggering loop

- **WHEN** the watchdog workflow itself runs (successfully or not)
- **THEN** it does not cause the watchdog workflow to trigger again

### Requirement: Diagnose from the failed run's logs

The agent SHALL fetch the logs of the failed run and read the relevant source
files to determine the root cause before taking any action.

#### Scenario: Logs and source are gathered

- **WHEN** the watchdog runs for a failed pipeline run
- **THEN** the agent retrieves the failed run's logs using the failed run's ID
- **AND** reads the relevant application source (e.g. `olx.py`, `main.py`)

### Requirement: Stay silent on transient failures

The agent SHALL classify the failure, and when it is transient (network error,
timeout, OLX 5xx/rate-limit, DNS), it SHALL take no action — no code change, no
pull request, and no notification — relying on the next scheduled run to self-heal.

#### Scenario: Transient failure detected

- **WHEN** the agent classifies the failure as transient
- **THEN** no pull request is opened
- **AND** the user is not notified

### Requirement: Open a review-only fix PR for code bugs

For a failure caused by a real code bug, the agent SHALL make the minimal fix on a
branch named `watchdog/fix-<run_id>` and open a pull request. The agent SHALL NOT
push to `main` directly and SHALL NOT auto-merge.

#### Scenario: Code bug is fixed and proposed

- **WHEN** the agent classifies the failure as a real code bug and produces a fix
- **THEN** the fix is committed to a `watchdog/fix-<run_id>` branch
- **AND** a pull request is opened from that branch targeting `main`
- **AND** `main` is not modified directly and the PR is not auto-merged

### Requirement: Verify the fix before proposing it

The agent SHALL run the existing `pytest` suite before opening the PR and SHALL
report the outcome truthfully in the PR body, including when tests fail or the fix
is uncertain.

#### Scenario: Tests pass

- **WHEN** the agent's fix makes `pytest` pass
- **THEN** the PR body states that `pytest` passed

#### Scenario: Tests fail or coverage is missing

- **WHEN** the agent cannot make `pytest` pass or no test covers the fixed path
- **THEN** the PR is still opened
- **AND** the PR body explicitly states the fix is unverified and needs manual review

### Requirement: Notify the user via the PR

The agent SHALL @mention and assign the repository owner on the fix PR so the user
is notified through GitHub's native channels. No email or Issue channel is used.

#### Scenario: User is notified on PR creation

- **WHEN** a fix PR is opened
- **THEN** the repository owner is @mentioned in the PR
- **AND** the PR is assigned to the repository owner
