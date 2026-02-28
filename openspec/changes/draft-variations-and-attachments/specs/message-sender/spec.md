## MODIFIED Requirements

### Requirement: Message sender supports media attachments
The POST /conversations/{id}/send endpoint SHALL accept multipart/form-data with an optional file field. When a file is present, the system SHALL determine the media type (image or document) and use the appropriate Evolution API endpoint (sendMedia or sendDocument). The file SHALL be sent as base64 in the API payload.

#### Scenario: Send text-only message
- **WHEN** the endpoint receives a request with text and no file
- **THEN** the system uses sendText (existing behavior unchanged)

#### Scenario: Send message with image
- **WHEN** the endpoint receives a request with text and a JPEG file
- **THEN** the system calls sendMedia with base64-encoded image and text as caption

#### Scenario: Send message with document
- **WHEN** the endpoint receives a request with text and a PDF file
- **THEN** the system calls sendDocument with base64-encoded PDF and text as filename caption

### Requirement: Edit pairs include expanded metadata
When creating edit_pairs, the system SHALL include all_drafts_json, selected_draft_index, operator_instruction, prompt_hash, and regeneration_count from the draft generation context.

#### Scenario: Edit pair with full context
- **WHEN** operator selects draft C, edits it, and sends
- **THEN** the edit_pair includes all 3 original drafts, selected_draft_index=2, the prompt hash, operator instruction (if any), and regeneration count
