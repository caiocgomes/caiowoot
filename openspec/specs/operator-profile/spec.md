## ADDED Requirements

### Requirement: Persist operator profiles in SQLite
The system SHALL store operator profiles in an `operator_profiles` table with columns: operator_name TEXT PRIMARY KEY, display_name TEXT, context TEXT, updated_at TIMESTAMP. Each operator has at most one profile row.

#### Scenario: Operator with existing profile
- **WHEN** the system reads the profile for an operator who has saved a profile
- **THEN** it SHALL return the stored display_name and context

#### Scenario: Operator without profile
- **WHEN** the system reads the profile for an operator who has never saved a profile
- **THEN** it SHALL return null/empty values for display_name and context

### Requirement: API for operator profile management
The system SHALL expose endpoints for reading and updating the logged-in operator's own profile.

#### Scenario: GET own profile
- **WHEN** an authenticated operator sends GET /api/settings/profile
- **THEN** the system SHALL return the profile for the operator identified in the session cookie
- **THEN** if no profile exists, it SHALL return empty/default values

#### Scenario: PUT own profile
- **WHEN** an authenticated operator sends PUT /api/settings/profile with display_name and context fields
- **THEN** the system SHALL upsert the profile for the operator identified in the session cookie
- **THEN** the `updated_at` timestamp SHALL be set to the current time

#### Scenario: Operator cannot edit another operator's profile
- **WHEN** an operator sends PUT /api/settings/profile
- **THEN** the system SHALL always use the operator name from the session cookie, ignoring any operator_name field in the request body

### Requirement: Operator context injected into draft prompt
The system SHALL inject the operator's context into the system prompt when generating drafts.

#### Scenario: Operator has context defined
- **WHEN** drafts are generated and the logged-in operator has a non-empty context in their profile
- **THEN** the system prompt SHALL include a section "## Sobre quem está respondendo" with the operator's context text
- **THEN** the opening paragraph SHALL use the operator's display_name (or operator_name if display_name is empty) instead of hardcoded "Caio"

#### Scenario: Operator has no profile or empty context
- **WHEN** drafts are generated and the logged-in operator has no profile or empty context
- **THEN** the system prompt SHALL NOT include the "Sobre quem está respondendo" section
- **THEN** the opening paragraph SHALL use the operator_name from the session

#### Scenario: No operator in session (auth disabled)
- **WHEN** drafts are generated and there is no operator in the session (APP_PASSWORD is empty)
- **THEN** the system SHALL use the current hardcoded behavior (default name "Caio", no profile section)
