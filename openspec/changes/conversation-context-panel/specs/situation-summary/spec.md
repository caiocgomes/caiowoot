## MODIFIED Requirements

### Requirement: Generate situation summary before drafts
The system SHALL generate a situation summary via Haiku before generating draft variations. The response SHALL be a JSON object with three fields: `summary` (2-3 sentence text), `product` (product identifier or null), `stage` (funnel stage or null). The `summary` field SHALL describe the strategic situation: stage of the conversation, apparent client profile, what has been discussed, and the expected next move.

#### Scenario: Summary for first contact
- **WHEN** a customer sends the first message in a conversation (e.g., "vi seu vídeo, quanto custa o curso?")
- **THEN** the situation summary SHALL return JSON with `summary` describing first contact and recommended approach, `product` as the inferred product or null, and `stage` as "qualifying"

#### Scenario: Summary for ongoing conversation
- **WHEN** a customer sends a message in an existing conversation with prior exchanges
- **THEN** the situation summary SHALL return JSON incorporating conversation history with appropriate `product` and `stage` reflecting current funnel position

#### Scenario: Summary includes conversation context
- **WHEN** the conversation has 3+ messages exchanged
- **THEN** the `summary` field SHALL reference specific information already gathered, and `product` and `stage` SHALL reflect the most current understanding

#### Scenario: JSON parse failure graceful degradation
- **WHEN** the Haiku response cannot be parsed as JSON
- **THEN** the system SHALL use the raw response text as the `summary` and set `product` and `stage` to null
