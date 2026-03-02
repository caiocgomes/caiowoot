## ADDED Requirements

### Requirement: Display context panel on desktop
The system SHALL display a right-side panel (`#context-panel`, ~280px) in the main area when a conversation is open on desktop. The panel SHALL be hidden on mobile (max-width: 767px).

#### Scenario: Panel visible when conversation open
- **WHEN** the operator opens a conversation on desktop
- **THEN** the context panel SHALL appear to the right of the chat area

#### Scenario: Panel hidden when no conversation
- **WHEN** no conversation is selected
- **THEN** the context panel SHALL not be visible

#### Scenario: Panel hidden on mobile
- **WHEN** the viewport width is below 768px
- **THEN** the context panel SHALL not be rendered

### Requirement: Display funnel product selector
The context panel SHALL display the current `funnel_product` as a dropdown/select with known products. The operator SHALL be able to change the product by selecting a different option.

#### Scenario: Show current product
- **WHEN** the conversation has `funnel_product` set to "curso-cdo"
- **THEN** the dropdown SHALL show "De Analista a CDO" as selected

#### Scenario: No product set
- **WHEN** the conversation has `funnel_product` as NULL
- **THEN** the dropdown SHALL show a placeholder (e.g., "Sem produto")

#### Scenario: Operator changes product
- **WHEN** the operator selects a different product in the dropdown
- **THEN** the system SHALL call PATCH /conversations/{id}/funnel with the new product

### Requirement: Display funnel stage indicator
The context panel SHALL display the current `funnel_stage` as a visual stepper or radio group showing all stages. The operator SHALL be able to change the stage by clicking.

#### Scenario: Show current stage
- **WHEN** the conversation has `funnel_stage` set to "handbook_sent"
- **THEN** the stage indicator SHALL highlight "Handbook enviado" as the current stage

#### Scenario: No stage set
- **WHEN** the conversation has `funnel_stage` as NULL
- **THEN** no stage SHALL be highlighted

#### Scenario: Operator changes stage
- **WHEN** the operator clicks a different stage
- **THEN** the system SHALL call PATCH /conversations/{id}/funnel with the new stage

### Requirement: Display conversation summary
The context panel SHALL display the most recent `situation_summary` as read-only text below the funnel controls.

#### Scenario: Summary available
- **WHEN** the conversation has drafts with a situation_summary
- **THEN** the panel SHALL display the most recent situation_summary text

#### Scenario: No summary available
- **WHEN** the conversation has no drafts or no situation_summary
- **THEN** the panel SHALL show a placeholder (e.g., "Sem resumo ainda")
