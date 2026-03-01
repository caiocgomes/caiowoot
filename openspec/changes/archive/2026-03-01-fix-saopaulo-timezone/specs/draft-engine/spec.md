## MODIFIED Requirements

### Requirement: Generate response drafts using Claude API
The system SHALL generate a draft response for each incoming customer message by calling the Claude API with a structured prompt containing: system instructions (tone, sales posture), active learned rules, knowledge base content, list of available attachments, situation summary, semantically similar few-shot examples from past edits (retrieved via ChromaDB) with attachment information when present, conversation history with timezone-aware timestamps, temporal context in the configured timezone, and operator instruction (if any).

#### Scenario: Temporal context uses configured timezone
- **WHEN** the draft engine builds temporal context for the prompt
- **THEN** the current time SHALL be obtained using the timezone configured in `Settings.timezone` (default: `America/Sao_Paulo`)
- **THEN** the "Agora são" timestamp SHALL reflect the configured timezone
- **THEN** the elapsed time calculation ("há Xh Ymin") SHALL compare the current timezone-aware time against the last inbound message timestamp converted to the same timezone

#### Scenario: Conversation history timestamps use configured timezone
- **WHEN** the draft engine formats timestamps for the last 10 messages in conversation history
- **THEN** each timestamp SHALL be displayed in the configured timezone
- **THEN** the "today" check (HH:MM vs DD/MM HH:MM format) SHALL use the current date in the configured timezone

#### Scenario: Greeting adjustment respects timezone
- **WHEN** the LLM receives the temporal context section
- **THEN** the "Agora são" time SHALL correctly reflect São Paulo local time so that greetings ("Bom dia", "Boa tarde", "Boa noite") are appropriate for the operator's timezone

#### Scenario: Draft generation for a new message
- **WHEN** the draft engine is invoked for a conversation with a new customer message
- **THEN** the system SHALL first generate a situation summary via Haiku
- **THEN** the system SHALL retrieve up to 5 semantically similar edit pairs from ChromaDB using the situation summary
- **THEN** the system SHALL send a prompt to Claude API containing: system prompt with active learned rules, knowledge base content, available attachments list, situation summary, retrieved few-shot examples (with strategic annotations and attachment info when available), full conversation history, and operator instruction
- **THEN** the response SHALL contain the draft text, a short justification, and optionally a suggested attachment filename

#### Scenario: Draft for first message in conversation
- **WHEN** the conversation has only one message (the customer's first contact)
- **THEN** the draft SHALL focus on greeting and qualifying the lead (understanding what they need) rather than immediately pitching a course

#### Scenario: Draft with attachment suggestion
- **WHEN** the LLM determines an attachment is appropriate based on the conversation context and learned patterns
- **THEN** the draft response SHALL include a `suggested_attachment` field with the filename of the suggested file
- **THEN** the suggested filename SHALL be validated against files in `knowledge/attachments/`
- **THEN** if the filename does not exist in the directory, the `suggested_attachment` field SHALL be discarded

#### Scenario: Draft without attachment suggestion
- **WHEN** the LLM determines no attachment is needed
- **THEN** the draft response SHALL have `suggested_attachment` as null or absent

#### Scenario: No known attachments available
- **WHEN** `knowledge/attachments/` is empty
- **THEN** the prompt SHALL NOT include the "Anexos disponíveis" section
- **THEN** the draft SHALL NOT include `suggested_attachment`

### Requirement: Use few-shot examples from edit history
The system SHALL select few-shot examples from stored edit pairs by querying ChromaDB for situation summaries most similar to the current situation summary. When no edit history exists, the system SHALL operate with zero-shot using only the system prompt, learned rules, and knowledge base.

#### Scenario: Sufficient edit history available
- **WHEN** there are 5+ stored edit pairs in ChromaDB
- **THEN** the system SHALL retrieve the 5 most similar edit pairs by situation summary similarity, prioritizing validated pairs
- **THEN** each few-shot example SHALL include: situation context, customer message, AI draft, operator's final message, strategic annotation (when available), and attachment filename (when present)

#### Scenario: Few-shot with attachment info
- **WHEN** a retrieved edit pair has a non-NULL `attachment_filename`
- **THEN** the few-shot example SHALL include a line: `Anexo enviado: <filename>`

#### Scenario: Few-shot without attachment info
- **WHEN** a retrieved edit pair has NULL `attachment_filename`
- **THEN** the few-shot example SHALL NOT include any attachment line

#### Scenario: No edit history available (cold start)
- **WHEN** there are no stored edit pairs in ChromaDB
- **THEN** the system SHALL generate drafts using only the system prompt, learned rules, knowledge base, and conversation history
