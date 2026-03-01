## ADDED Requirements

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
