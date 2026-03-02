## ADDED Requirements

### Requirement: Persist prompt sections in SQLite
The system SHALL store editable prompt sections in a `prompt_config` table with key-value schema (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TIMESTAMP). The editable keys SHALL be: `postura`, `tom`, `regras`, `approach_direta`, `approach_consultiva`, `approach_casual`, `summary_prompt`, `annotation_prompt`.

#### Scenario: Read prompt config with all keys populated
- **WHEN** the system reads prompt config from the database
- **THEN** it SHALL return the stored value for each key

#### Scenario: Read prompt config with missing key
- **WHEN** the system reads a prompt config key that does not exist in the database
- **THEN** it SHALL return the hardcoded default value for that key

#### Scenario: Update prompt config key
- **WHEN** an admin updates a prompt config key via the API
- **THEN** the system SHALL upsert the key-value pair in `prompt_config`
- **THEN** the `updated_at` timestamp SHALL be set to the current time
- **THEN** the next draft generation SHALL use the new value

### Requirement: API for prompt config management
The system SHALL expose endpoints for reading and updating prompt config, restricted to admin.

#### Scenario: GET prompts as any authenticated operator
- **WHEN** any authenticated operator sends GET /api/settings/prompts
- **THEN** the system SHALL return all 8 prompt sections with their current values (from DB or hardcoded defaults)

#### Scenario: PUT prompts as admin
- **WHEN** the admin operator sends PUT /api/settings/prompts with a JSON body containing one or more prompt keys
- **THEN** the system SHALL update each provided key in the database
- **THEN** keys not included in the request SHALL remain unchanged

#### Scenario: PUT prompts as non-admin
- **WHEN** a non-admin operator sends PUT /api/settings/prompts
- **THEN** the system SHALL return 403 Forbidden

#### Scenario: Reset prompt to default
- **WHEN** the admin sends PUT /api/settings/prompts with a key set to null or empty string
- **THEN** the system SHALL delete that key from the database
- **THEN** subsequent reads SHALL return the hardcoded default for that key

### Requirement: Admin identity check
The system SHALL determine admin status from the `ADMIN_OPERATOR` env var. If not set, the first operator in the `OPERATORS` list SHALL be considered admin.

#### Scenario: ADMIN_OPERATOR env var is set
- **WHEN** `ADMIN_OPERATOR` is set to "Caio"
- **THEN** only the operator "Caio" SHALL be recognized as admin

#### Scenario: ADMIN_OPERATOR env var is not set
- **WHEN** `ADMIN_OPERATOR` is not set and `OPERATORS` is "Caio,João,Vitória"
- **THEN** "Caio" (first in list) SHALL be recognized as admin

#### Scenario: No operators configured
- **WHEN** `OPERATORS` is empty and `ADMIN_OPERATOR` is not set
- **THEN** all authenticated users SHALL be treated as admin (no restriction)

#### Scenario: Check admin status via API
- **WHEN** an authenticated operator sends GET /api/settings/is-admin
- **THEN** the system SHALL return `{"is_admin": true}` or `{"is_admin": false}`
