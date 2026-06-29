## ADDED Requirements

### Requirement: Persist seen listing IDs

The system SHALL persist the set of seen listing IDs in `state/seen.json` as a
JSON list of strings. The system SHALL provide `load_seen()` returning the
stored set and `save_seen(ids)` writing the set back. When no state file
exists, `load_seen()` SHALL return an empty set.

#### Scenario: Load existing state
- **WHEN** `state/seen.json` exists with a list of IDs
- **THEN** `load_seen()` returns those IDs as a set of strings

#### Scenario: Load with no prior state
- **WHEN** `state/seen.json` does not exist
- **THEN** `load_seen()` returns an empty set

#### Scenario: Save state
- **WHEN** `save_seen(ids)` is called
- **THEN** `state/seen.json` contains exactly those IDs as a JSON list

### Requirement: Compute new listings

The system SHALL compute the set of new listings as those current listings
whose ID is not in the seen set.

#### Scenario: Some listings are new
- **WHEN** the current listings include IDs not present in the seen set
- **THEN** only the listings with unseen IDs are returned as new

#### Scenario: No new listings
- **WHEN** every current listing ID is already in the seen set
- **THEN** the new set is empty

### Requirement: First-run bootstrap

On the first run (no prior state), the system SHALL record all currently
visible listing IDs as seen and SHALL NOT emit any notification. Notifications
begin only on subsequent runs.

#### Scenario: First run records but does not notify
- **WHEN** a run executes and no prior state exists
- **THEN** all current listing IDs are saved as seen and no notification is sent

### Requirement: Bounded state size

The system SHALL cap the persisted seen set to the most recent ~1000 IDs so the
state file does not grow unbounded, retaining the newest IDs when trimming.

#### Scenario: State exceeds the cap
- **WHEN** the seen set would exceed the cap after adding new IDs
- **THEN** the system retains the most recent IDs up to the cap and discards the oldest
