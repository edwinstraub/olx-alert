## ADDED Requirements

### Requirement: Pluggable notifier interface

The system SHALL define a `Notifier` interface with a `send(new_listings)`
method. Notification channels SHALL be implementations of this interface, so a
new channel can be added without changes to fetching, state, or orchestration.
The active channel SHALL be selectable via configuration.

#### Scenario: Send through the configured notifier
- **WHEN** a run has new listings and a notifier is configured
- **THEN** the orchestrator calls `send(new_listings)` on that notifier implementation

#### Scenario: Adding a channel requires no core changes
- **WHEN** a new notifier implementation is added and selected in config
- **THEN** fetching, state, and orchestration code are unchanged

### Requirement: Email notifier

The system SHALL provide an `EmailNotifier` that sends new-listing
notifications over Gmail SMTP authenticated with an App Password. SMTP
credentials SHALL be read from the `SMTP_USER` and `SMTP_PASS` environment
variables (sourced from GitHub Secrets); the recipient address SHALL be read
from `config.yaml`.

#### Scenario: Send an email for new listings
- **WHEN** `EmailNotifier.send(new_listings)` is called with one or more listings
- **THEN** an email is sent via Gmail SMTP to the configured recipient using the credentials from the environment

### Requirement: Email content

The notification email subject SHALL summarize the count of new listings (e.g.
`🏍️ 2 new motorcycle listings on OLX`). The body SHALL list each new listing
with its title, price, location, posted time, and a direct link, rendering with
whatever fields are available when some are missing.

#### Scenario: Subject summarizes count
- **WHEN** an email is rendered for N new listings
- **THEN** the subject reflects the count of new listings

#### Scenario: Body lists each listing with a link
- **WHEN** an email is rendered
- **THEN** the body contains, for each new listing, its available fields and a direct link to the listing

#### Scenario: Partial fields still render
- **WHEN** a listing is missing price, location, or posted time
- **THEN** the email still renders that listing using its available fields

### Requirement: State advances only after successful send

The system SHALL advance persisted state only after a notification is sent
successfully. If sending fails, state SHALL NOT advance so the same new
listings are retried on the next run.

#### Scenario: Send fails
- **WHEN** `send(new_listings)` raises or fails
- **THEN** the seen state is not updated and the run fails so the listings are retried next run

#### Scenario: Send succeeds
- **WHEN** `send(new_listings)` completes successfully
- **THEN** the new listing IDs are added to the seen state and persisted
