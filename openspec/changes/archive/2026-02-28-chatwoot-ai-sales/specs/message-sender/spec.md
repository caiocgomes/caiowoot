## ADDED Requirements

### Requirement: Send messages via Evolution API
The system SHALL send text messages to WhatsApp contacts by calling the Evolution API send message endpoint. The message SHALL be sent to the contact's phone number in the context of the active conversation.

#### Scenario: Successful message send
- **WHEN** the operator submits a message from the UI
- **THEN** the system SHALL call the Evolution API send endpoint with the message text and recipient phone number
- **THEN** the sent message SHALL be persisted in the conversation with a "sent" status and timestamp

#### Scenario: Evolution API send failure
- **WHEN** the Evolution API returns an error on send
- **THEN** the system SHALL display an error notification in the UI
- **THEN** the message text SHALL remain in the textarea so the operator can retry

### Requirement: Record edit pairs for learning loop
The system SHALL store each (original draft, final sent message) pair whenever the operator sends a message that originated from an IA draft. This record SHALL include: the customer message that triggered the draft, the original draft text, the final sent text, and the timestamp.

#### Scenario: Operator edits draft before sending
- **WHEN** the operator modifies the IA draft and sends
- **THEN** the system SHALL store both the original draft and the final version as an edit pair

#### Scenario: Operator sends draft unedited
- **WHEN** the operator sends the IA draft without changes
- **THEN** the system SHALL store the pair with a flag indicating no edit was made (useful for tracking acceptance rate)

#### Scenario: Operator writes message manually (no draft)
- **WHEN** the operator clears the draft and writes a message from scratch, or sends when no draft was available
- **THEN** the system SHALL NOT create an edit pair (no original draft to compare)
