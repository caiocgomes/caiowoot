## MODIFIED Requirements

### Requirement: Generate response drafts using Claude API
The system SHALL generate a draft response for each incoming customer message by calling the Claude API with a structured prompt composed of: fixed infrastructure sections (WhatsApp formatting, temporal context, attachment instructions, JSON response format) combined with editable sections read from the `prompt_config` table (postura, tom, regras) with hardcoded fallback defaults, the logged-in operator's profile context (if available), active learned rules, knowledge base content, list of available attachments, situation summary, semantically similar few-shot examples from past edits (retrieved via ChromaDB) with attachment information when present, conversation history with timezone-aware timestamps on recent messages, temporal context in the configured timezone (current time, client wait time), and operator instruction (if any). The situation summary prompt and annotation prompt SHALL also be read from `prompt_config` with hardcoded fallback defaults. When invoked with `proactive=True`, the final instruction SHALL change from generating a response to the client's last message to generating a natural continuation of the conversation.

#### Scenario: Draft generation reads prompts from database
- **WHEN** the draft engine is invoked for a conversation
- **THEN** the system SHALL read prompt sections (postura, tom, regras, approach modifiers) from the `prompt_config` table
- **THEN** for any key not present in the database, the system SHALL use the hardcoded default value
- **THEN** the system prompt SHALL be assembled by combining fixed infrastructure sections with the database-sourced editable sections

#### Scenario: Draft generation includes operator profile
- **WHEN** the draft engine is invoked and the operator has a non-empty profile context
- **THEN** the opening paragraph of the system prompt SHALL use the operator's display name
- **THEN** the system prompt SHALL include a "## Sobre quem está respondendo" section with the operator's context text

#### Scenario: Draft generation without operator profile
- **WHEN** the draft engine is invoked and the operator has no profile or empty context
- **THEN** the system SHALL assemble the prompt using the operator_name from the session (or default "Caio" if no session)
- **THEN** the "Sobre quem está respondendo" section SHALL be omitted

#### Scenario: Situation summary uses configurable prompt
- **WHEN** the system generates a situation summary
- **THEN** it SHALL read the `summary_prompt` key from `prompt_config`
- **THEN** if the key is not present, it SHALL use the hardcoded SUMMARY_PROMPT default

#### Scenario: Strategic annotation uses configurable prompt
- **WHEN** the system generates a strategic annotation
- **THEN** it SHALL read the `annotation_prompt` key from `prompt_config`
- **THEN** if the key is not present, it SHALL use the hardcoded ANNOTATION_PROMPT default

#### Scenario: Approach modifiers use configurable values
- **WHEN** the draft engine generates 3 variations
- **THEN** it SHALL read `approach_direta`, `approach_consultiva`, `approach_casual` from `prompt_config`
- **THEN** each variation SHALL use its corresponding configurable modifier text
- **THEN** if a key is missing from the database, the system SHALL use the hardcoded default modifier

#### Scenario: Draft generation for a new message
- **WHEN** the draft engine is invoked for a conversation with a new customer message
- **THEN** the system SHALL first generate a situation summary via Haiku
- **THEN** the system SHALL retrieve up to 5 semantically similar edit pairs from ChromaDB using the situation summary
- **THEN** the system SHALL send a prompt to Claude API containing: assembled system prompt with active learned rules, knowledge base content, available attachments list, situation summary, retrieved few-shot examples (with strategic annotations and attachment info when available), conversation history with timestamps on the last 10 messages, temporal context section, and operator instruction
- **THEN** the response SHALL contain the draft text, a short justification, and optionally a suggested attachment filename

#### Scenario: Proactive draft generation for followup
- **WHEN** the draft engine is invoked with `proactive=True`
- **THEN** the system SHALL follow the same prompt-building pipeline (situation summary, few-shot retrieval, knowledge base, rules, temporal context)
- **THEN** the final instruction SHALL be "A última mensagem da conversa foi enviada pelo {operator_name}. Gere uma mensagem de continuação natural, retomando o contexto da conversa." instead of "Gere o draft de resposta para a última mensagem do cliente."

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

#### Scenario: Conversation history includes timestamps on recent messages
- **WHEN** the conversation has more than 10 messages
- **THEN** messages older than the last 10 SHALL be formatted as `Cliente: texto` or `{operator_name}: texto` without timestamps
- **THEN** the last 10 messages SHALL be formatted as `[HH:MM] Cliente: texto` for messages from today, or `[DD/MM HH:MM] Cliente: texto` for messages from previous days

#### Scenario: Conversation history with 10 or fewer messages
- **WHEN** the conversation has 10 or fewer messages
- **THEN** all messages SHALL include timestamps in the same format

#### Scenario: Temporal context section included in prompt
- **WHEN** the draft engine builds the prompt
- **THEN** the prompt SHALL include a temporal context section after the conversation history containing: the current time formatted as `HH:MM (DD/MM)`, and the elapsed time since the last inbound message from the client

#### Scenario: Significant response delay
- **WHEN** the elapsed time since the last client message exceeds 1 hour
- **THEN** the temporal context section SHALL note the delay explicitly (e.g., "Última mensagem do cliente foi há 3h 15min")

#### Scenario: Recent client message
- **WHEN** the elapsed time since the last client message is under 1 hour
- **THEN** the temporal context section SHALL note the time simply (e.g., "Última mensagem do cliente foi há 12min")

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
