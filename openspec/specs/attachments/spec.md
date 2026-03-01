## ADDED Requirements

### Requirement: Operator can attach files to outgoing messages
The system SHALL provide an attachment button in the compose area. The operator SHALL be able to select a file (image, PDF, document) from the local machine. A preview/indicator of the attached file SHALL appear before sending.

#### Scenario: Attach an image
- **WHEN** operator clicks the attach button and selects a JPG file
- **THEN** a thumbnail preview appears in the compose area alongside the textarea

#### Scenario: Attach a PDF
- **WHEN** operator clicks the attach button and selects a PDF file
- **THEN** the filename and file type icon appear in the compose area

#### Scenario: Remove attachment before sending
- **WHEN** operator clicks the remove button on an attached file
- **THEN** the attachment is removed and only text will be sent

### Requirement: System sends attachments via Evolution API media endpoints
The system SHALL send attachments using the Evolution API's sendMedia (for images) or sendDocument (for PDFs/documents) endpoints. The file SHALL be sent as base64-encoded data in the API payload.

#### Scenario: Send message with image attachment
- **WHEN** operator sends a message with an attached image
- **THEN** the system calls Evolution API's sendMedia endpoint with the image as base64 and the text as caption

#### Scenario: Send message with document attachment
- **WHEN** operator sends a message with an attached PDF
- **THEN** the system calls Evolution API's sendDocument endpoint with the file as base64

#### Scenario: Send message without attachment
- **WHEN** operator sends a message with no attachment
- **THEN** the system uses the existing sendText endpoint (no change from current behavior)

### Requirement: Outbound messages with attachments are persisted
The system SHALL persist outbound messages that include attachments with media_url and media_type fields in the messages table.

#### Scenario: Message with attachment saved to database
- **WHEN** an outbound message with a PDF attachment is sent successfully
- **THEN** the message record includes media_type="document" and media_url pointing to the stored file
