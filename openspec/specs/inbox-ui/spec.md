## ADDED Requirements

### Requirement: Display conversation list
The system SHALL display a list of all conversations in a sidebar, ordered by most recent message. Each entry SHALL show: contact name or phone number, preview of the last message (truncated), timestamp of last message, and unread indicator if there are customer messages without a sent reply.

#### Scenario: Conversations with unread messages
- **WHEN** the operator opens the inbox
- **THEN** conversations with unanswered customer messages SHALL appear with a visual unread indicator
- **THEN** conversations SHALL be sorted by most recent message first

#### Scenario: Conversation list updates in real time
- **WHEN** a new message arrives while the operator has the inbox open
- **THEN** the conversation list SHALL update without requiring a page refresh (via WebSocket)

### Requirement: Display message thread
The system SHALL display the full message history of a selected conversation, with clear visual distinction between customer messages and operator messages.

#### Scenario: Viewing a conversation
- **WHEN** the operator clicks a conversation in the list
- **THEN** all messages in that conversation SHALL be displayed in chronological order
- **THEN** customer messages and operator messages SHALL be visually distinct (e.g., left-aligned vs right-aligned, different background colors)

### Requirement: Display editable draft with justification
When a draft is available for the current conversation, the system SHALL display it in an editable textarea below the message thread, along with the IA justification above or beside the textarea. The operator SHALL be able to edit the draft freely before sending.

#### Scenario: Draft ready when conversation opened
- **WHEN** the operator opens a conversation that has a pending draft
- **THEN** the draft text SHALL appear in an editable textarea
- **THEN** the IA justification SHALL appear as a non-editable note near the textarea

#### Scenario: Draft arrives while viewing conversation
- **WHEN** the operator is viewing a conversation and a draft finishes generating
- **THEN** the draft SHALL appear in the textarea without disrupting any text the operator may have already started typing

#### Scenario: No draft available
- **WHEN** the operator opens a conversation without a pending draft
- **THEN** an empty textarea SHALL be displayed for manual message composition

### Requirement: Send message from UI
The system SHALL provide a send button that submits the content of the textarea (edited draft or manually written message) to the message sender backend.

#### Scenario: Sending an edited draft
- **WHEN** the operator edits the draft and clicks send
- **THEN** the final text SHALL be sent to the backend for delivery via Evolution API
- **THEN** the sent message SHALL appear in the message thread immediately
- **THEN** the textarea SHALL be cleared

#### Scenario: Sending without editing
- **WHEN** the operator clicks send without editing the draft
- **THEN** the draft text SHALL be sent as-is
