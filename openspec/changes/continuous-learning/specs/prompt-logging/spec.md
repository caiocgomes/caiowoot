## MODIFIED Requirements

### Requirement: Edit pairs record expanded metadata for tuning
The edit_pairs table SHALL be expanded to include: operator_instruction, all_drafts_json (all 3 variations), selected_draft_index (which was chosen), prompt_hash (reference to the prompt file), regeneration_count, situation_summary, strategic_annotation, validated (boolean default false), rejected (boolean default false).

#### Scenario: Edit pair created with full metadata
- **WHEN** operator selects draft B, edits it, and sends
- **THEN** the edit_pair record contains: customer_message, operator_instruction (or null), all_drafts_json with all 3 draft texts, selected_draft_index=1, original_draft=draft B text, final_message=edited text, was_edited=true, prompt_hash=sha256, regeneration_count=N, situation_summary from the draft group

#### Scenario: Edit pair without operator instruction
- **WHEN** operator sends without having used the instruction bar
- **THEN** operator_instruction is stored as NULL

#### Scenario: Regeneration count tracked
- **WHEN** operator regenerates 2 times before selecting and sending
- **THEN** regeneration_count is stored as 2

#### Scenario: Strategic annotation added asynchronously
- **WHEN** the background annotation task completes after send
- **THEN** the edit pair's strategic_annotation field SHALL be updated with the generated annotation text

#### Scenario: Validation state tracked
- **WHEN** the operator reviews an annotation in the learning review UI
- **THEN** the validated field SHALL be set to true
- **THEN** the rejected field SHALL reflect whether the operator confirmed or rejected the annotation
