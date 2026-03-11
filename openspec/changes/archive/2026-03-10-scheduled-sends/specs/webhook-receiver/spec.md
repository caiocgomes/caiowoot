## MODIFIED Requirements

### Requirement: Receive incoming WhatsApp messages via Evolution API webhook
The system SHALL expose an HTTP POST endpoint that receives webhook payloads from Evolution API when new WhatsApp messages arrive. The endpoint SHALL validate the payload structure and ignore non-message events (status updates, ack events, etc). The webhook endpoint SHALL be accessible without authentication (exempt from the password gate middleware). Upon receiving a valid inbound message, the system SHALL cancel all pending scheduled sends for that conversation.

#### Scenario: New text message received
- **WHEN** Evolution API sends a webhook with a text message from a contact
- **THEN** the system SHALL extract sender phone number, message text, timestamp, and message ID, and persist them in the database

#### Scenario: Non-message event received
- **WHEN** Evolution API sends a webhook for a status update or delivery receipt
- **THEN** the system SHALL return 200 OK and take no further action

#### Scenario: Duplicate message received
- **WHEN** Evolution API sends a webhook with a message ID that already exists in the database
- **THEN** the system SHALL ignore the duplicate and return 200 OK

#### Scenario: Webhook accessible without authentication
- **WHEN** Evolution API posts to /webhook without a session cookie
- **THEN** the system SHALL process the webhook normally (no authentication required)

#### Scenario: Inbound message cancels pending scheduled sends
- **WHEN** a valid inbound message is received for a conversation that has pending scheduled sends
- **THEN** the system SHALL cancel all pending scheduled sends for that conversation with reason `client_replied` and the inbound message ID
- **THEN** the system SHALL broadcast a `scheduled_send_cancelled` WebSocket event for each cancelled send
