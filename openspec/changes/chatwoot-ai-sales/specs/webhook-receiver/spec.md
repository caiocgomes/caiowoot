## ADDED Requirements

### Requirement: Receive incoming WhatsApp messages via Evolution API webhook
The system SHALL expose an HTTP POST endpoint that receives webhook payloads from Evolution API when new WhatsApp messages arrive. The endpoint SHALL validate the payload structure and ignore non-message events (status updates, ack events, etc).

#### Scenario: New text message received
- **WHEN** Evolution API sends a webhook with a text message from a contact
- **THEN** the system SHALL extract sender phone number, message text, timestamp, and message ID, and persist them in the database

#### Scenario: Non-message event received
- **WHEN** Evolution API sends a webhook for a status update or delivery receipt
- **THEN** the system SHALL return 200 OK and take no further action

#### Scenario: Duplicate message received
- **WHEN** Evolution API sends a webhook with a message ID that already exists in the database
- **THEN** the system SHALL ignore the duplicate and return 200 OK

### Requirement: Persist conversations with automatic grouping
The system SHALL group messages into conversations by sender phone number. Each conversation SHALL track: contact phone number, contact name (from WhatsApp profile if available), list of messages ordered by timestamp, and conversation status (active/archived).

#### Scenario: First message from a new contact
- **WHEN** a message arrives from a phone number not seen before
- **THEN** the system SHALL create a new conversation record and store the message as the first entry

#### Scenario: Subsequent message from existing contact
- **WHEN** a message arrives from a phone number with an existing conversation
- **THEN** the system SHALL append the message to the existing conversation

### Requirement: Trigger draft generation on incoming message
The system SHALL trigger the draft engine immediately when a new customer message is received, so the draft is ready when the operator opens the conversation.

#### Scenario: Message received triggers draft
- **WHEN** a new customer message is persisted
- **THEN** the system SHALL asynchronously invoke the draft engine for that conversation
- **THEN** the generated draft SHALL be stored associated with the conversation and the triggering message
