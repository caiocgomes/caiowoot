## ADDED Requirements

### Requirement: Store learned rules in database
The system SHALL maintain a learned_rules table that stores rules promoted from strategic annotations. Each rule SHALL have: id, rule_text (free-form text), source_edit_pair_id (optional reference to the originating edit pair), is_active (boolean), created_at, updated_at.

#### Scenario: Rule created from promotion
- **WHEN** an annotation is promoted to a rule
- **THEN** a new row is inserted in learned_rules with rule_text, source_edit_pair_id linking to the originating edit pair, and is_active=true

#### Scenario: Rule created manually
- **WHEN** the operator creates a rule directly (without promoting from annotation)
- **THEN** a new row is inserted with rule_text, source_edit_pair_id=NULL, and is_active=true

### Requirement: Inject active rules into system prompt
The system SHALL collect all active learned rules and inject them into the system prompt in a dedicated section. Rules SHALL appear after the base system prompt instructions and before the knowledge base.

#### Scenario: Rules present in prompt
- **WHEN** there are 3 active learned rules
- **THEN** the system prompt SHALL contain a section "## Regras aprendidas" listing all 3 rules as numbered items

#### Scenario: No active rules
- **WHEN** there are no active learned rules
- **THEN** the system prompt SHALL NOT include the "Regras aprendidas" section

### Requirement: Manage learned rules via API
The system SHALL expose API endpoints to list, create, update, and toggle (activate/deactivate) learned rules.

#### Scenario: List all rules
- **WHEN** a GET request is made to the rules endpoint
- **THEN** the system SHALL return all learned rules ordered by created_at, including active and inactive

#### Scenario: Update rule text
- **WHEN** the operator edits a rule's text
- **THEN** the rule_text SHALL be updated and updated_at SHALL reflect the modification time

#### Scenario: Deactivate a rule
- **WHEN** the operator deactivates a rule
- **THEN** is_active SHALL be set to false
- **THEN** the rule SHALL no longer appear in the system prompt
- **THEN** the rule SHALL remain in the database for potential reactivation

#### Scenario: Reactivate a rule
- **WHEN** the operator reactivates a previously deactivated rule
- **THEN** is_active SHALL be set to true
- **THEN** the rule SHALL appear in the system prompt again
