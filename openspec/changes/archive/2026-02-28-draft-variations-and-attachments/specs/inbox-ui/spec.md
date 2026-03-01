## MODIFIED Requirements

### Requirement: Compose area displays draft variations for selection
The compose area SHALL display 3 draft variation cards above the textarea. Each card SHALL show a truncated preview of the draft text, a select button, and an individual regenerate button. A "regenerate all" button SHALL appear alongside the cards. The textarea SHALL be larger (minimum 5 visible lines) to facilitate reading and editing longer responses.

#### Scenario: Draft cards appear when drafts arrive
- **WHEN** 3 draft variations are received via WebSocket
- **THEN** 3 cards appear above the textarea, each showing the draft preview

#### Scenario: Selecting a card populates textarea
- **WHEN** operator clicks select on a card
- **THEN** the full draft text fills the textarea and the selected card is visually highlighted

#### Scenario: Textarea is large enough for comfortable editing
- **WHEN** the compose area is displayed
- **THEN** the textarea shows at least 5 lines of text without scrolling

### Requirement: Instruction bar for operator context
The compose area SHALL include an instruction input bar between the draft cards and the textarea. This bar allows the operator to type context or direction for the AI. A "regenerate with instruction" button SHALL trigger regeneration using the instruction text.

#### Scenario: Operator types instruction and regenerates
- **WHEN** operator types "ela é técnica" in the instruction bar and clicks regenerate
- **THEN** a POST request is sent to the regenerate endpoint with the instruction text

### Requirement: Attachment upload in compose area
The compose area SHALL include an attach button (paperclip icon) next to the send button. Clicking it SHALL open a file picker. After selecting a file, a preview/indicator SHALL appear in the compose area. A remove button SHALL allow removing the attachment before sending.

#### Scenario: File attached and previewed
- **WHEN** operator selects a file via the attach button
- **THEN** the file name and a remove button appear in the compose area

#### Scenario: Message sent with attachment
- **WHEN** operator clicks send with a file attached
- **THEN** the request is sent as multipart/form-data with both text and file
