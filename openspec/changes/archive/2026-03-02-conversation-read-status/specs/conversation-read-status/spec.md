## ADDED Requirements

### Requirement: Track conversation read status
The system SHALL track when the operator last viewed each conversation via a `last_read_at` timestamp on the `conversations` table.

#### Scenario: Opening a conversation updates last_read_at
- **WHEN** the operator opens a conversation via `GET /conversations/{id}`
- **THEN** the system SHALL update `last_read_at` to the current timestamp for that conversation

#### Scenario: New conversation has null last_read_at
- **WHEN** a new conversation is created by an inbound webhook
- **THEN** `last_read_at` SHALL be NULL

### Requirement: Conversation list returns is_new and needs_reply flags
The conversation list endpoint SHALL return `is_new` and `needs_reply` flags for each conversation instead of the current `has_unread`.

#### Scenario: Message arrived after last read
- **WHEN** a conversation has an inbound message with `created_at` after `last_read_at`
- **THEN** `is_new` SHALL be true and `needs_reply` SHALL be true

#### Scenario: Message read but not replied
- **WHEN** the operator has opened the conversation (last_read_at updated) but the last message is still inbound
- **THEN** `is_new` SHALL be false and `needs_reply` SHALL be true

#### Scenario: Operator has replied
- **WHEN** the last message in the conversation is outbound
- **THEN** `is_new` SHALL be false and `needs_reply` SHALL be false

#### Scenario: Conversation never opened
- **WHEN** `last_read_at` is NULL and there are inbound messages
- **THEN** `is_new` SHALL be true and `needs_reply` SHALL be true
