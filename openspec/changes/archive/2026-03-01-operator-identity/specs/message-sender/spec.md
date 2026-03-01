## MODIFIED Requirements

### Requirement: Send messages via Evolution API
The system SHALL send text messages to WhatsApp contacts by calling the Evolution API send message endpoint. The message SHALL be sent to the contact's phone number in the context of the active conversation. The system SHALL record the operator's name (from the session) in the `sent_by` column of the message record for outbound messages.

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
