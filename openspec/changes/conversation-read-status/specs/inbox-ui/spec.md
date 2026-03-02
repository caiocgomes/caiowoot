## MODIFIED Requirements

### Requirement: Display last responder in conversation list
The conversation list SHALL display the name of the operator who sent the last outbound message in each conversation. The name SHALL appear below the message preview text. Each conversation item SHALL also display visual indicators based on `is_new` and `needs_reply` flags: a green dot and bold name for new messages, bold name only for conversations awaiting reply.

#### Scenario: Conversation has outbound messages with sent_by
- **WHEN** the conversation list loads and a conversation has outbound messages with `sent_by` set
- **THEN** the system SHALL display the operator name of the most recent outbound message below the preview

#### Scenario: Conversation has no outbound messages
- **WHEN** the conversation list loads and a conversation has no outbound messages
- **THEN** the system SHALL not display any operator name

#### Scenario: Last outbound message has no sent_by
- **WHEN** the conversation list loads and the most recent outbound message has `sent_by` as NULL (pre-migration message)
- **THEN** the system SHALL not display any operator name for that conversation

#### Scenario: New message indicator
- **WHEN** a conversation has `is_new` = true
- **THEN** the system SHALL display a green dot before the contact name and render the name in bold

#### Scenario: Needs reply indicator
- **WHEN** a conversation has `is_new` = false and `needs_reply` = true
- **THEN** the system SHALL render the contact name in bold (no green dot)

#### Scenario: No pending action
- **WHEN** a conversation has `is_new` = false and `needs_reply` = false
- **THEN** the system SHALL render the contact name in normal weight (no dot, no bold)
