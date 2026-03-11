## ADDED Requirements

### Requirement: Reject duplicate outbound messages within 5-second window
The system SHALL reject sending a message if an identical outbound message was sent to the same conversation within the last 5 seconds.

#### Scenario: Duplicate message within 5 seconds
- **WHEN** the operator sends a message with content identical to the last outbound message in the same conversation
- **AND** the last outbound message was sent less than 5 seconds ago
- **THEN** the system SHALL reject the send with HTTP 409 Conflict and a clear error message

#### Scenario: Same message after 5 seconds
- **WHEN** the operator sends a message with content identical to a previous outbound message
- **AND** the previous message was sent more than 5 seconds ago
- **THEN** the system SHALL send the message normally

#### Scenario: Different message within 5 seconds
- **WHEN** the operator sends a message with different content than the last outbound message
- **AND** the last outbound message was sent less than 5 seconds ago
- **THEN** the system SHALL send the message normally

#### Scenario: First message in conversation
- **WHEN** the operator sends a message in a conversation with no previous outbound messages
- **THEN** the system SHALL send the message normally
