## ADDED Requirements

### Requirement: System generates three draft variations per incoming message
The system SHALL generate 3 distinct draft responses for each incoming customer message, using Claude Haiku in parallel (asyncio.gather). Each variation SHALL use a different approach instruction (e.g., direct/consultive/casual) to produce meaningfully different responses, not just paraphrases.

#### Scenario: Three drafts generated on new message
- **WHEN** a customer message is received via webhook
- **THEN** the system generates 3 draft variations in parallel and notifies the frontend via WebSocket with all 3 drafts

#### Scenario: Parallel generation completes within acceptable latency
- **WHEN** 3 Haiku calls are made in parallel via asyncio.gather
- **THEN** total latency is approximately the same as a single call (not 3x)

### Requirement: Operator selects one draft variation to use
The system SHALL display 3 draft cards above the compose textarea. The operator SHALL click a selection button on one card to populate the textarea with that draft text.

#### Scenario: Selecting a draft populates textarea
- **WHEN** operator clicks the select button on draft variation B
- **THEN** the textarea is populated with draft B's text and the current draft ID is set to B's ID

#### Scenario: Selection does not auto-send
- **WHEN** operator selects a draft
- **THEN** the draft appears in the textarea for editing but is NOT sent automatically

### Requirement: Operator can regenerate individual drafts or all three
The system SHALL provide a regenerate button on each individual draft card and a "regenerate all" button. Regeneration SHALL use the current operator instruction (if any) as additional context.

#### Scenario: Regenerate single draft
- **WHEN** operator clicks regenerate on draft A
- **THEN** only draft A is regenerated (new Haiku call) while B and C remain unchanged

#### Scenario: Regenerate all drafts
- **WHEN** operator clicks "regenerate all"
- **THEN** all 3 drafts are regenerated in parallel with fresh Haiku calls

#### Scenario: Regeneration uses operator instruction
- **WHEN** operator has typed "foca no preço" in the instruction bar and clicks regenerate
- **THEN** the regenerated draft(s) incorporate that instruction in the prompt

### Requirement: Operator instruction bar provides context to AI
The system SHALL display an instruction input bar between the draft cards and the compose textarea. Text entered in this bar SHALL be appended to the prompt when generating or regenerating drafts. The instruction bar content persists until the operator clears it.

#### Scenario: Instruction included in prompt
- **WHEN** operator types "esse lead é técnico, pode falar de arquitetura" and regenerates
- **THEN** the prompt sent to Haiku includes this instruction as additional context

#### Scenario: Empty instruction bar
- **WHEN** the instruction bar is empty and drafts are generated
- **THEN** drafts are generated without additional operator instruction (same as current behavior)
