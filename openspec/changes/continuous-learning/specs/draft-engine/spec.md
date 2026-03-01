## MODIFIED Requirements

### Requirement: Generate response drafts using Claude API
The system SHALL generate a draft response for each incoming customer message by calling the Claude API with a structured prompt containing: system instructions (tone, sales posture), active learned rules, knowledge base content, situation summary, semantically similar few-shot examples from past edits (retrieved via ChromaDB), conversation history, and operator instruction (if any).

#### Scenario: Draft generation for a new message
- **WHEN** the draft engine is invoked for a conversation with a new customer message
- **THEN** the system SHALL first generate a situation summary via Haiku
- **THEN** the system SHALL retrieve up to 5 semantically similar edit pairs from ChromaDB using the situation summary
- **THEN** the system SHALL send a prompt to Claude API containing: system prompt with active learned rules, knowledge base content, situation summary, retrieved few-shot examples (with strategic annotations when available), full conversation history, and operator instruction
- **THEN** the response SHALL contain the draft text and a short justification explaining the chosen approach

#### Scenario: Draft for first message in conversation
- **WHEN** the conversation has only one message (the customer's first contact)
- **THEN** the draft SHALL focus on greeting and qualifying the lead (understanding what they need) rather than immediately pitching a course

### Requirement: Use few-shot examples from edit history
The system SHALL select few-shot examples from stored edit pairs by querying ChromaDB for situation summaries most similar to the current situation summary. When no edit history exists, the system SHALL operate with zero-shot using only the system prompt, learned rules, and knowledge base.

#### Scenario: Sufficient edit history available
- **WHEN** there are 5+ stored edit pairs in ChromaDB
- **THEN** the system SHALL retrieve the 5 most similar edit pairs by situation summary similarity, prioritizing validated pairs
- **THEN** each few-shot example SHALL include: situation context, customer message, AI draft, operator's final message, and strategic annotation (when available)

#### Scenario: No edit history available (cold start)
- **WHEN** there are no stored edit pairs in ChromaDB
- **THEN** the system SHALL generate drafts using only the system prompt, learned rules, knowledge base, and conversation history
