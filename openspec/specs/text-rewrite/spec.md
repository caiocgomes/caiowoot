## ADDED Requirements

### Requirement: Rewrite endpoint accepts text and returns polished version
The system SHALL expose `POST /conversations/{conversation_id}/rewrite` that receives a JSON body with `text` (string) and returns `{"text": "<rewritten>"}`. The endpoint SHALL call Claude Haiku with a fixed prompt that rewrites the input preserving exact semantic content, fixing Portuguese grammar and spelling, and using a WhatsApp-appropriate tone. The endpoint SHALL NOT add new information, change the meaning, or restructure the argument beyond clarity improvements.

#### Scenario: Successful rewrite of rough text
- **WHEN** operator sends POST to `/conversations/{id}/rewrite` with `{"text": "oi maria, entao o curso ele tem 12 modulos e vc vai ter acesso por 1 ano. o preço ta 997 mas da pra parcelar em 12x"}`
- **THEN** the system SHALL return 200 with `{"text": "<polished version>"}` where the polished version fixes grammar and formatting but keeps the same information about 12 modules, 1 year access, R$997, and 12x installments

#### Scenario: Empty text
- **WHEN** operator sends POST with `{"text": ""}` or missing text field
- **THEN** the system SHALL return 422 validation error

#### Scenario: Conversation not found
- **WHEN** operator sends POST to `/conversations/99999/rewrite`
- **THEN** the system SHALL return 404

### Requirement: Rewrite service uses isolated prompt
The text rewrite service SHALL use a dedicated module (`app/services/text_rewrite.py`) with a fixed system prompt. The service SHALL NOT depend on conversation context, knowledge base, situation summary, or any other draft engine infrastructure. The LLM call SHALL use `tool_use` for structured output, following the project's existing pattern.

#### Scenario: Service independence
- **WHEN** the rewrite function is called with a text string
- **THEN** it SHALL make a single Haiku API call with only the system prompt and the user's text, without querying the database or loading conversation history
