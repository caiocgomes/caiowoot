## MODIFIED Requirements

### Requirement: Operator selects one draft variation to use
The system SHALL display 3 draft cards in a horizontal carousel above the compose textarea. The operator SHALL tap a card to select it, which populates the textarea with that draft text. The selected card SHALL change to primary background with white text. **CHANGE:** Visual presentation changes from side-by-side row to horizontal carousel with scroll-snap. Selection visual changes from green highlight to primary-background fill.

#### Scenario: Selecting a draft populates textarea
- **WHEN** operator taps draft card B
- **THEN** the textarea is populated with draft B's text and the current draft ID is set to B's ID
- **THEN** card B SHALL have `--primary` background with white text
- **THEN** cards A and C SHALL have white background

#### Scenario: Selection does not auto-send
- **WHEN** operator selects a draft
- **THEN** the draft appears in the textarea for editing but is NOT sent automatically

### Requirement: Operator instruction bar provides context to AI
The system SHALL display a refinement input below the AI Copilot message and above the draft cards, with a `psychology_alt` icon and placeholder text. Text entered SHALL be used as `operator_instruction` when generating or regenerating drafts. A refresh button next to the input SHALL trigger regeneration. **CHANGE:** Visual redesign from instruction bar in compose area to inline refinement input positioned between AI message and draft cards, with new icon and placeholder text.

#### Scenario: Refinement input visible after AI response
- **WHEN** an AI Copilot message and draft cards are displayed
- **THEN** the refinement input SHALL be visible between the message and drafts with `psychology_alt` icon

#### Scenario: Instruction bar visible without drafts
- **WHEN** automatic draft generation fails and no draft cards are displayed
- **THEN** the refinement input with the regenerate button SHALL still be visible

#### Scenario: Instruction included in prompt
- **WHEN** operator types "esse lead é técnico, pode falar de arquitetura" and clicks the refresh button
- **THEN** the prompt sent to Haiku includes this instruction as additional context

#### Scenario: Empty refinement input
- **WHEN** the refinement input is empty and drafts are regenerated
- **THEN** drafts are generated without additional operator instruction
