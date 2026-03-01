## ADDED Requirements

### Requirement: Generate situation summary before drafts
The system SHALL generate a situation summary (2-3 sentences) via Haiku before generating draft variations. The summary SHALL describe the strategic situation: stage of the conversation, apparent client profile, what has been discussed, and the expected next move.

#### Scenario: Summary for first contact
- **WHEN** a customer sends the first message in a conversation (e.g., "vi seu vídeo, quanto custa o curso?")
- **THEN** the situation summary SHALL describe: first contact, no prior qualification, customer's apparent intent, and recommended strategic approach (e.g., "Primeiro contato. Cliente demonstra interesse genérico após ver conteúdo no Instagram. Pergunta preço direto sem contexto sobre perfil ou objetivos. Nenhuma qualificação feita. Momento de qualificar antes de precificar.")

#### Scenario: Summary for ongoing conversation
- **WHEN** a customer sends a message in an existing conversation with prior exchanges
- **THEN** the situation summary SHALL incorporate conversation history: what has been discussed, what the operator has already qualified, current stage (qualifying, recommending, handling objection, closing)

#### Scenario: Summary includes conversation context
- **WHEN** the conversation has 3+ messages exchanged
- **THEN** the situation summary SHALL reference specific information already gathered (e.g., "Cliente é desenvolvedor Python, busca transição para dados. Já qualificado como perfil técnico intermediário. Objeção de preço ativa.")

### Requirement: Summary is included in draft prompt as explicit context
The generated situation summary SHALL be inserted into the prompt sent to generate draft variations, in a dedicated section before the conversation history. All 3 draft variations SHALL receive the same situation summary.

#### Scenario: Summary present in prompt
- **WHEN** drafts are generated for a conversation
- **THEN** the prompt SHALL contain a section "## Situação atual" with the situation summary text, positioned after knowledge base and before few-shot examples

### Requirement: Summary is persisted with the draft group
The situation summary SHALL be stored in the database associated with the draft group so it can be saved with the edit pair for future retrieval.

#### Scenario: Summary stored on draft generation
- **WHEN** a draft group is generated for a conversation
- **THEN** the situation_summary text is stored in the drafts table (all drafts in the group share the same summary)

#### Scenario: Summary carried to edit pair on send
- **WHEN** the operator sends a message (edited or not) based on a draft
- **THEN** the edit pair record SHALL include the situation_summary from the draft group
