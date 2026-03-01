## ADDED Requirements

### Requirement: Configure operators via environment variable
The system SHALL read a comma-separated list of operator names from the `OPERATORS` environment variable. The list SHALL be parsed at startup and made available to the login flow. Each name SHALL be trimmed of leading/trailing whitespace.

#### Scenario: OPERATORS configured
- **WHEN** the application starts with `OPERATORS=Caio,João,Maria`
- **THEN** the system SHALL make the list `["Caio", "João", "Maria"]` available for operator selection

#### Scenario: OPERATORS not configured
- **WHEN** the application starts without `OPERATORS` set or with an empty value
- **THEN** the system SHALL skip operator selection entirely and function as before (no operator tracking)

### Requirement: Select operator name at login
The system SHALL present a list of configured operator names during the login flow. The operator MUST select their name before gaining access to the application. The selected name SHALL be stored in the session cookie payload alongside the authentication flag.

#### Scenario: Operator selects name during login
- **WHEN** the operator submits correct password and selects "Caio" from the operator list
- **THEN** the system SHALL set the session cookie with `{"authenticated": true, "operator": "Caio"}`

#### Scenario: Operator submits login without selecting name
- **WHEN** the operator submits correct password but does not select a name
- **THEN** the system SHALL reject the login and display an error message

#### Scenario: No operators configured
- **WHEN** `OPERATORS` is not set and the operator submits correct password
- **THEN** the system SHALL set the session cookie with `{"authenticated": true}` (no operator field, backward compatible)

### Requirement: Expose current operator name to frontend
The system SHALL provide an API endpoint that returns the current operator's name from the session cookie. The frontend SHALL use this to display who is logged in.

#### Scenario: Authenticated request to /api/me
- **WHEN** an authenticated operator requests GET /api/me
- **THEN** the system SHALL return `{"operator": "Caio"}` (or `{"operator": null}` if no operator in session)
