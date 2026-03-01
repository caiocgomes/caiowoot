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

### Requirement: Display last responder in conversation list
The conversation list SHALL display the name of the operator who sent the last outbound message in each conversation. The name SHALL appear below the message preview text.

#### Scenario: Conversation has outbound messages with sent_by
- **WHEN** the conversation list loads and a conversation has outbound messages with `sent_by` set
- **THEN** the system SHALL display the operator name of the most recent outbound message below the preview

#### Scenario: Conversation has no outbound messages
- **WHEN** the conversation list loads and a conversation has no outbound messages
- **THEN** the system SHALL not display any operator name

#### Scenario: Last outbound message has no sent_by
- **WHEN** the conversation list loads and the most recent outbound message has `sent_by` as NULL (pre-migration message)
- **THEN** the system SHALL not display any operator name for that conversation
