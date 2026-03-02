## ADDED Requirements

### Requirement: Track funnel product and stage per conversation
The system SHALL store `funnel_product` (TEXT, nullable) and `funnel_stage` (TEXT, nullable) on each conversation. Valid stages are: `qualifying`, `decided`, `handbook_sent`, `link_sent`, `purchased`.

#### Scenario: New conversation has no funnel data
- **WHEN** a new conversation is created by an inbound webhook
- **THEN** `funnel_product` and `funnel_stage` SHALL be NULL

#### Scenario: Funnel data persisted on conversation
- **WHEN** the AI or operator sets funnel_product to "curso-cdo" and funnel_stage to "qualifying"
- **THEN** the conversation record SHALL store those values

### Requirement: AI automatically updates funnel from situation summary
The system SHALL update `funnel_product` and `funnel_stage` on the conversation when generating drafts, using the structured output from the situation summary.

#### Scenario: AI detects product interest
- **WHEN** drafts are generated and the situation summary extracts product "curso-zero-a-analista" and stage "qualifying"
- **THEN** the system SHALL UPDATE the conversation's `funnel_product` and `funnel_stage`

#### Scenario: AI extraction fails gracefully
- **WHEN** the situation summary fails to extract structured product/stage (JSON parse error)
- **THEN** the system SHALL NOT update funnel fields and SHALL continue with draft generation normally

#### Scenario: AI updates stage progression
- **WHEN** the conversation progresses (e.g., operator sent handbook) and new drafts are generated
- **THEN** the AI SHALL update `funnel_stage` to reflect the new stage (e.g., `handbook_sent`)

### Requirement: Operator can manually correct funnel data
The system SHALL provide `PATCH /conversations/{id}/funnel` to update funnel_product and/or funnel_stage.

#### Scenario: Update both fields
- **WHEN** the operator sends PATCH with `{"funnel_product": "curso-cdo", "funnel_stage": "decided"}`
- **THEN** the system SHALL update both fields on the conversation

#### Scenario: Update single field
- **WHEN** the operator sends PATCH with `{"funnel_stage": "link_sent"}`
- **THEN** the system SHALL update only `funnel_stage`, leaving `funnel_product` unchanged

#### Scenario: Invalid stage rejected
- **WHEN** the operator sends PATCH with `{"funnel_stage": "invalid_value"}`
- **THEN** the system SHALL return 422 with error message

#### Scenario: Conversation not found
- **WHEN** the operator sends PATCH for a non-existent conversation_id
- **THEN** the system SHALL return 404
