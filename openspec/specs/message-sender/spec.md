## ADDED Requirements

### Requirement: Send messages via Evolution API
The system SHALL send text messages to WhatsApp contacts by calling the Evolution API send message endpoint. The message SHALL be sent to the contact's phone number in the context of the active conversation. The system SHALL record the operator's name (from the session) in the `sent_by` column of the message record for outbound messages. The core send logic (Evolution API call, message persistence, edit_pair creation, WebSocket broadcast) SHALL be encapsulated in a shared function usable by both the immediate send endpoint and the scheduled send background worker.

#### Scenario: Successful message send
- **WHEN** the operator submits a message from the UI
- **THEN** the system SHALL call the Evolution API send endpoint with the message text and recipient phone number
- **THEN** the sent message SHALL be persisted in the conversation with a "sent" status, timestamp, and `sent_by` set to the current operator's name

#### Scenario: Evolution API send failure
- **WHEN** the Evolution API returns an error on send
- **THEN** the system SHALL display an error notification in the UI
- **THEN** the message text SHALL remain in the textarea so the operator can retry

#### Scenario: Message sent without operator in session
- **WHEN** the operator sends a message and the session has no operator field
- **THEN** the system SHALL persist the message with `sent_by` as NULL

#### Scenario: Scheduled send uses shared send logic
- **WHEN** the background worker sends a scheduled message
- **THEN** the system SHALL use the same shared send function as the immediate send endpoint
- **THEN** the `sent_by` field SHALL be set to the operator who originally scheduled the message

### Requirement: Record edit pairs for learning loop
The system SHALL store each (original draft, final sent message) pair whenever the operator sends a message that originated from an IA draft. This record SHALL include: the customer message that triggered the draft, the original draft text, the final sent text, the attachment filename (if any), and the timestamp.

#### Scenario: Operator edits draft before sending
- **WHEN** the operator modifies the IA draft and sends
- **THEN** the system SHALL store both the original draft and the final version as an edit pair

#### Scenario: Operator sends draft unedited
- **WHEN** the operator sends the IA draft without changes
- **THEN** the system SHALL store the pair with a flag indicating no edit was made (useful for tracking acceptance rate)

#### Scenario: Operator writes message manually (no draft)
- **WHEN** the operator clears the draft and writes a message from scratch, or sends when no draft was available
- **THEN** the system SHALL NOT create an edit pair (no original draft to compare)

#### Scenario: Operator sends message with attachment from draft
- **WHEN** the operator sends a message with an attached file and the message originated from a draft
- **THEN** the edit pair SHALL include `attachment_filename` with the name of the attached file

#### Scenario: Operator sends message without attachment
- **WHEN** the operator sends a message without any attachment
- **THEN** the edit pair SHALL have `attachment_filename` as NULL

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
