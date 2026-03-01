## MODIFIED Requirements

### Requirement: Draft engine generates AI-powered response drafts
The system SHALL generate 3 draft variations in parallel using Claude Haiku (claude-haiku-4-5-20251001) instead of 1 draft with Sonnet. Each variation SHALL use a different approach modifier appended to the system prompt (e.g., "responda de forma mais direta", "responda de forma mais consultiva", "responda de forma mais casual"). The system SHALL accept an optional operator_instruction parameter that is appended to the user prompt when provided. The prompt assembly (system prompt, knowledge base, few-shot, history) remains unchanged.

#### Scenario: Three variations generated in parallel
- **WHEN** a new customer message triggers draft generation
- **THEN** 3 parallel Haiku API calls are made, each with a different approach modifier, and all 3 results are saved and broadcast via WebSocket

#### Scenario: Operator instruction included in prompt
- **WHEN** generate_drafts is called with operator_instruction="foca no preço"
- **THEN** all 3 API calls include "Instrução do operador: foca no preço" in the user prompt

#### Scenario: Prompt hash saved to disk
- **WHEN** drafts are generated
- **THEN** the full prompt text is saved to data/prompts/{hash}.txt and the hash is stored with the draft records
