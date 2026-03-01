## ADDED Requirements

### Requirement: Full prompt saved to disk as hash-named file
The system SHALL compute a SHA-256 hash of the complete prompt (system + knowledge + few-shot + history + instruction) and save the full prompt text to `data/prompts/{hash}.txt`. If the file already exists (same hash), it SHALL NOT be overwritten.

#### Scenario: Prompt saved on draft generation
- **WHEN** the draft engine generates drafts for a conversation
- **THEN** a file named `data/prompts/{sha256_hash}.txt` is created containing the full prompt text

#### Scenario: Duplicate prompt reuses existing file
- **WHEN** the same prompt is used again (e.g., regeneration without changes)
- **THEN** no new file is created; the existing hash file is reused

### Requirement: Edit pairs record expanded metadata for tuning
The edit_pairs table SHALL be expanded to include: operator_instruction, all_drafts_json (all 3 variations), selected_draft_index (which was chosen), prompt_hash (reference to the prompt file), and regeneration_count.

#### Scenario: Edit pair created with full metadata
- **WHEN** operator selects draft B, edits it, and sends
- **THEN** the edit_pair record contains: customer_message, operator_instruction (or null), all_drafts_json with all 3 draft texts, selected_draft_index=1, original_draft=draft B text, final_message=edited text, was_edited=true, prompt_hash=sha256, regeneration_count=N

#### Scenario: Edit pair without operator instruction
- **WHEN** operator sends without having used the instruction bar
- **THEN** operator_instruction is stored as NULL

#### Scenario: Regeneration count tracked
- **WHEN** operator regenerates 2 times before selecting and sending
- **THEN** regeneration_count is stored as 2
