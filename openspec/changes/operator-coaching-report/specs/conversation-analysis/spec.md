## ADDED Requirements

### Requirement: Assess individual conversation quality via LLM
The system SHALL analyze each conversation that had outbound activity in a given period by sending the full conversation context to an LLM (Haiku). The input SHALL include: all messages in chronological order with sender identity (sent_by) and timestamps, all edit_pairs with was_edited/strategic_annotation/selected_draft_index/regeneration_count, the relevant knowledge base content, and computed response times (time between inbound message and next outbound). The output SHALL be a structured JSON assessment.

#### Scenario: Conversation with edit pairs analyzed
- **WHEN** an analysis run processes a conversation that has edit_pairs
- **THEN** the LLM SHALL receive the conversation messages, edit_pair data (including was_edited, strategic_annotation, all_drafts_json), and knowledge base
- **THEN** the LLM SHALL return a JSON object with: factual_issues (array of {message_excerpt, claim, knowledge_says, severity}), engagement_level ("high"/"medium"/"low"), engagement_notes (text), sale_status ("active"/"cooling"/"dead"/"converted"), recovery_potential ("high"/"medium"/"low"/"none"), recovery_suggestion (text or null), overall_assessment (text)

#### Scenario: Conversation without edit pairs analyzed
- **WHEN** an analysis run processes a conversation where operator typed messages directly (no edit_pairs)
- **THEN** the LLM SHALL still analyze the messages for factual accuracy against knowledge base and engagement quality
- **THEN** edit-related metrics (was_edited, draft acceptance) SHALL be noted as "sem dados de draft"

#### Scenario: Factual error detection against knowledge base
- **WHEN** the LLM identifies an operator statement that contradicts the knowledge base
- **THEN** it SHALL include an entry in factual_issues with the message excerpt, what the operator claimed, and what the knowledge base says
- **THEN** severity SHALL be "high" if it affects pricing/content/eligibility, "medium" otherwise

#### Scenario: Factual claim not in knowledge base
- **WHEN** the operator states something that the knowledge base does not cover (neither confirms nor denies)
- **THEN** it SHALL NOT be flagged as a factual error
- **THEN** it MAY be noted in overall_assessment as "informacao nao verificavel"

#### Scenario: Engagement level assessment
- **WHEN** the LLM evaluates engagement level
- **THEN** "low" SHALL be assigned when responses are generic, short for the context, lack personalization (no reference to client-specific details), or fail to advance the conversation (no follow-up question)
- **THEN** "high" SHALL be assigned when responses reference client-specific context, show genuine interest, and proactively advance the sale

#### Scenario: Pilot-mode detection
- **WHEN** the operator accepted all drafts without editing (was_edited=false on all edit_pairs)
- **THEN** the assessment SHALL explicitly note this pattern in overall_assessment
- **THEN** engagement_level SHALL be at most "medium" regardless of draft quality, because accepting everything without review indicates lack of operator judgment

#### Scenario: Sale status classification
- **WHEN** the LLM classifies sale_status
- **THEN** "active" means client is actively engaged and responding
- **THEN** "cooling" means client stopped responding or said "vou pensar" without follow-up
- **THEN** "dead" means client explicitly declined or has been unresponsive for 3+ days
- **THEN** "converted" means a sale was completed (detectable from conversation content)

#### Scenario: Recovery suggestion for cooling/dead conversations
- **WHEN** sale_status is "cooling" or "dead" AND recovery_potential is "medium" or "high"
- **THEN** recovery_suggestion SHALL contain a specific, actionable suggestion for how to re-engage the client, referencing concrete details from the conversation

### Requirement: Persist conversation assessments
The system SHALL store conversation assessments in a `conversation_assessments` SQLite table with columns: id, analysis_run_id, conversation_id, operator_name, engagement_level, sale_status, recovery_potential, recovery_suggestion, factual_issues_json, overall_assessment, created_at.

#### Scenario: Assessment persisted after LLM call
- **WHEN** the LLM returns a conversation assessment
- **THEN** the system SHALL insert a row into conversation_assessments with all fields populated
- **THEN** factual_issues SHALL be stored as JSON array in factual_issues_json column

#### Scenario: Assessment for multi-operator conversation
- **WHEN** a conversation was handled by more than one operator (different sent_by values)
- **THEN** the system SHALL create one assessment per operator, each covering only the messages that operator sent and the context around them

### Requirement: Compute quantitative metrics per conversation-operator pair
Before calling the LLM, the system SHALL compute and include in the prompt: total messages sent by this operator in this conversation, draft acceptance rate (% of edit_pairs with was_edited=false), average regeneration count, time-to-respond distribution (median and max gap between inbound and next outbound by this operator), approaches selected distribution (count of direta/consultiva/casual).

#### Scenario: Metrics computed for prompt context
- **WHEN** the analysis processes a conversation-operator pair
- **THEN** these metrics SHALL be computed from edit_pairs and messages tables
- **THEN** they SHALL be included in the LLM prompt as structured context under "## Metricas do operador nesta conversa"
