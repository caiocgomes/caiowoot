## MODIFIED Requirements

### Requirement: Operator instruction bar provides context to AI
The system SHALL display an instruction input bar in the compose area **whenever a conversation is open**, regardless of whether drafts exist. Text entered in this bar SHALL be appended to the prompt when generating or regenerating drafts. The instruction bar content persists until the operator clears it.

#### Scenario: Instruction bar visible on conversation open
- **WHEN** the operator opens any conversation
- **THEN** the instruction bar with the regenerate button SHALL be visible in the compose area

#### Scenario: Instruction bar visible without drafts
- **WHEN** automatic draft generation fails and no draft cards are displayed
- **THEN** the instruction bar with the regenerate button SHALL still be visible

#### Scenario: Instruction included in prompt
- **WHEN** operator types "esse lead é técnico, pode falar de arquitetura" and clicks regenerate
- **THEN** the prompt sent to Haiku includes this instruction as additional context

#### Scenario: Empty instruction bar
- **WHEN** the instruction bar is empty and drafts are generated
- **THEN** drafts are generated without additional operator instruction

## ADDED Requirements

### Requirement: Regenerate works without prior drafts
The regenerate button in the instruction bar SHALL work even when no drafts have been previously generated for the current conversation. The system SHALL identify the last inbound message in the conversation and use its ID as the trigger_message_id for draft generation.

#### Scenario: Regenerate with no existing drafts (inbound last message)
- **WHEN** the operator clicks the regenerate button and no drafts exist for the conversation
- **AND** the last message in the conversation is inbound
- **THEN** the system SHALL call `POST /conversations/{id}/regenerate` with `trigger_message_id` set to the last inbound message ID and `draft_index: null`

#### Scenario: Regenerate with no existing drafts (outbound last message)
- **WHEN** the operator clicks the regenerate button and no drafts exist for the conversation
- **AND** the last message in the conversation is outbound
- **THEN** the system SHALL call `POST /conversations/{id}/regenerate` with `trigger_message_id` set to the last message ID and `draft_index: null`

#### Scenario: Regenerate with existing drafts (unchanged behavior)
- **WHEN** the operator clicks the regenerate button and drafts exist
- **THEN** the system SHALL use the existing `currentDrafts[0].trigger_message_id` as before

### Requirement: Frontend tracks last inbound message ID
The frontend SHALL maintain a `lastInboundMessageId` variable that is updated when opening a conversation and when receiving new inbound messages via WebSocket.

#### Scenario: Set on conversation open
- **WHEN** the operator opens a conversation
- **THEN** `lastInboundMessageId` SHALL be set to the ID of the last inbound message in the conversation, or the last message ID if none is inbound

#### Scenario: Updated on new inbound message
- **WHEN** a `new_message` WebSocket event is received for the current conversation with direction "inbound"
- **THEN** `lastInboundMessageId` SHALL be updated to the new message's ID
