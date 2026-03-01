## ADDED Requirements

### Requirement: Display active rules in learning tab
The learning tab SHALL display a list of active learned rules below the pending annotations section. Each rule SHALL show its text and allow toggle (on/off) and inline text editing.

#### Scenario: View active rules
- **WHEN** the operator opens the Aprendizado tab
- **THEN** the system SHALL display all learned rules with their active/inactive status

#### Scenario: Toggle rule
- **WHEN** the operator toggles a rule
- **THEN** the system SHALL call PATCH /rules/{id}/toggle and update the UI

#### Scenario: Edit rule text
- **WHEN** the operator edits a rule's text and saves
- **THEN** the system SHALL call PUT /rules/{id} with the new text

### Requirement: Display review history stats
The learning tab SHALL display history stats showing how many annotations have been validated, rejected, and promoted to rules.

#### Scenario: History stats visible
- **WHEN** the operator opens the Aprendizado tab
- **THEN** stats SHALL show counts for validated, rejected, and promoted annotations
