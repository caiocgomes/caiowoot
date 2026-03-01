## ADDED Requirements

### Requirement: Generate response drafts using Claude API
The system SHALL generate a draft response for each incoming customer message by calling the Claude API with a structured prompt containing: system instructions (tone, sales posture), knowledge base content, conversation history, and few-shot examples from past edits.

#### Scenario: Draft generation for a new message
- **WHEN** the draft engine is invoked for a conversation with a new customer message
- **THEN** the system SHALL send a prompt to Claude API containing the full conversation history, relevant knowledge base content, and up to 10 most relevant few-shot examples
- **THEN** the response SHALL contain the draft text and a short justification (1-2 sentences) explaining the chosen approach

#### Scenario: Draft for first message in conversation
- **WHEN** the conversation has only one message (the customer's first contact)
- **THEN** the draft SHALL focus on greeting and qualifying the lead (understanding what they need) rather than immediately pitching a course

### Requirement: Include sales strategy context in prompts
The system prompt SHALL instruct the LLM to behave as a consultive seller: qualifying leads before recommending, handling objections by showing relative value (not discounting), being direct without being pushy, and being willing to say "this course might not be for you" when appropriate.

#### Scenario: Price objection detected
- **WHEN** the customer message contains a price objection (e.g., "é caro", "não tenho grana", "tem desconto")
- **THEN** the draft SHALL address the objection through value anchoring (ROI, daily cost breakdown, comparison with alternatives) rather than offering discounts

#### Scenario: Vague interest without specifics
- **WHEN** the customer expresses generic interest (e.g., "quero aprender IA", "vi seu vídeo")
- **THEN** the draft SHALL ask a qualifying question to understand the customer's background and goals before recommending a specific course

### Requirement: Provide approach justification with each draft
Each draft SHALL include a short justification explaining why the IA chose that approach (e.g., "qualifiquei como insegurança técnica, foquei em remover barreira" or "objeção de preço, ancorei em ROI"). This justification SHALL be displayed to the operator but NOT sent to the customer.

#### Scenario: Justification displayed
- **WHEN** a draft is generated and shown in the UI
- **THEN** the justification text SHALL appear visually separated from the draft message text
- **THEN** the operator SHALL be able to read the justification to quickly assess if the approach is appropriate

### Requirement: Use few-shot examples from edit history
The system SHALL select few-shot examples from the stored (draft, final message) pairs, prioritizing examples where the customer message is semantically similar to the current one. When no edit history exists, the system SHALL operate with zero-shot using only the system prompt and knowledge base.

#### Scenario: Sufficient edit history available
- **WHEN** there are 5+ stored edit pairs
- **THEN** the system SHALL select the most relevant examples by similarity to the current customer message and include them in the prompt

#### Scenario: No edit history available (cold start)
- **WHEN** there are no stored edit pairs
- **THEN** the system SHALL generate drafts using only the system prompt, knowledge base, and conversation history
