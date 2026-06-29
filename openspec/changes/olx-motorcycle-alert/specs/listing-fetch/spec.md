## ADDED Requirements

### Requirement: Fetch listings for a search URL

The system SHALL fetch the current motorcycle listings for a user-provided
OLX.ro search-results URL and return them as a list of normalized `Listing`
value objects. The system SHALL prefer structured JSON data when available and
SHALL fall back to parsing the HTML search page when JSON is unavailable.

#### Scenario: Fetch returns listings from JSON
- **WHEN** `fetch_listings(search_url)` is called and OLX returns structured JSON offers
- **THEN** the system returns one `Listing` per offer with its fields populated from the JSON

#### Scenario: Fetch falls back to HTML parsing
- **WHEN** structured JSON is unavailable but the HTML search page is returned
- **THEN** the system parses the HTML and returns one `Listing` per listing found on the page

### Requirement: Stable listing ID is the only required field

Each `Listing` SHALL carry a stable alphanumeric ID extracted from the listing
URL (e.g. `.../d/oferta/...-ID<alnum>.html`, such as `IDkAZhr`). The ID is
stored as a string. It is the only field required for correctness; all other
fields (title, price, location, posted time, url) are best-effort.

#### Scenario: Every listing has an ID
- **WHEN** listings are parsed from JSON or HTML
- **THEN** each returned `Listing` has a non-empty string `id` extracted from its URL

#### Scenario: Missing optional fields do not drop a listing
- **WHEN** a listing is missing its price, location, or posted time
- **THEN** the `Listing` is still returned, with the missing fields left empty rather than omitting the listing

### Requirement: Fetch failure is signaled, not masked

The system SHALL distinguish a successful fetch from a failure. On a network
error, non-success HTTP status, or unparseable response, the system SHALL raise
or otherwise signal a fetch failure rather than returning an empty list as if
it were a valid result.

#### Scenario: Network or HTTP error
- **WHEN** the request to OLX fails with a network error or a non-success HTTP status
- **THEN** the system signals a fetch failure (does not return an empty list as a normal result)

#### Scenario: Unparseable response
- **WHEN** the response body cannot be parsed as either JSON offers or listing HTML
- **THEN** the system signals a fetch failure
