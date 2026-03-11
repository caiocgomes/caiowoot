## ADDED Requirements

### Requirement: Track analysis runs
The system SHALL maintain an `analysis_runs` table with columns: id, period_start (TEXT ISO date), period_end (TEXT ISO date), status ("running"/"completed"/"failed"), total_conversations (INTEGER), total_operators (INTEGER), error_message (TEXT nullable), created_at, completed_at. Each analysis execution creates one run record.

#### Scenario: Analysis run created
- **WHEN** an analysis is triggered (manual or scheduled)
- **THEN** a new row SHALL be inserted with status="running" and the specified period
- **THEN** upon completion, status SHALL be updated to "completed" with completed_at timestamp and counts

#### Scenario: Analysis run fails
- **WHEN** an error occurs during analysis processing
- **THEN** status SHALL be set to "failed" with error_message populated
- **THEN** any assessments already created in this run SHALL be preserved (partial results are valuable)

#### Scenario: Duplicate run prevention
- **WHEN** an analysis is triggered for a period that already has a "completed" run
- **THEN** the system SHALL proceed and create a new run (allowing re-analysis)
- **THEN** previous results SHALL NOT be deleted (history is preserved)

### Requirement: Generate operator digest via LLM
The system SHALL generate a per-operator digest by sending all conversation_assessments for that operator in the analysis period to an LLM (Sonnet). The digest SHALL identify behavioral patterns with concrete examples from the operator's actual conversations.

#### Scenario: Operator digest generation
- **WHEN** all conversation assessments for an operator are complete
- **THEN** the system SHALL send to Sonnet: the list of assessments, the aggregated metrics (total conversations, overall draft acceptance rate, conversations by sale_status, factual issues count), and the operator's profile context
- **THEN** Sonnet SHALL return a JSON with: summary (2-3 sentence overall assessment), patterns (array of {pattern, examples, suggestion}), factual_issues_highlight (array of most critical errors with conversation references), salvageable_sales (array of {conversation_id, contact_name, situation, suggestion, priority})

#### Scenario: Pattern identification with examples
- **WHEN** the digest LLM identifies a behavioral pattern (e.g., "aceita drafts sem editar")
- **THEN** each pattern SHALL include at least one concrete example referencing a specific conversation and message
- **THEN** each pattern SHALL include a specific suggestion for improvement

#### Scenario: Salvageable sales list generation
- **WHEN** the digest processes assessments with recovery_potential "medium" or "high"
- **THEN** these SHALL be collected into salvageable_sales, ordered by priority ("high" first)
- **THEN** each entry SHALL include the contact_name, a brief situation description, and a concrete suggestion for re-engagement

#### Scenario: Operator with no issues
- **WHEN** all conversations have high engagement and no factual issues
- **THEN** the digest SHALL still be generated, noting positive patterns and what works well

### Requirement: Persist operator digests
The system SHALL store operator digests in an `operator_digests` table with columns: id, analysis_run_id, operator_name, summary, patterns_json, factual_issues_json, salvageable_sales_json, metrics_json, created_at.

#### Scenario: Digest persisted
- **WHEN** the LLM returns an operator digest
- **THEN** the system SHALL insert a row with all fields as JSON where applicable

### Requirement: Admin-only analysis trigger endpoint
The system SHALL provide POST /admin/analysis/run accepting optional JSON body with period_start and period_end (ISO date strings). Only admin users (is_admin() = true) SHALL access this endpoint. If no period specified, SHALL default to yesterday (00:00 to 23:59).

#### Scenario: Admin triggers analysis
- **WHEN** an admin user sends POST /admin/analysis/run with {"period_start": "2026-03-01", "period_end": "2026-03-07"}
- **THEN** the system SHALL create an analysis run and begin processing in background (asyncio.create_task)
- **THEN** the endpoint SHALL return immediately with {"run_id": <id>, "status": "running"}

#### Scenario: Non-admin denied
- **WHEN** a non-admin user sends POST /admin/analysis/run
- **THEN** the system SHALL return 403 Forbidden

#### Scenario: Default period
- **WHEN** admin sends POST /admin/analysis/run without period parameters
- **THEN** the system SHALL analyze yesterday (from 00:00:00 to 23:59:59 local time)

### Requirement: Admin-only coaching page
The system SHALL serve a coaching page at GET /admin/coaching accessible only to admin users. The page SHALL display the most recent analysis run results.

#### Scenario: Coaching page layout
- **WHEN** admin visits /admin/coaching
- **THEN** the page SHALL show:
  1. Header with analysis period and run timestamp
  2. "Vendas para salvar" section first, aggregating all salvageable_sales across operators, ordered by priority
  3. Per-operator sections, each showing: operator name, key metrics (messages sent, draft acceptance rate, conversations count, sales converted), summary text, identified patterns with examples, factual issues if any
  4. A "Rodar analise" button to trigger a new run with date range picker

#### Scenario: No analysis results
- **WHEN** admin visits /admin/coaching and no analysis has been run
- **THEN** the page SHALL show the "Rodar analise" button and a message indicating no results yet

#### Scenario: Non-admin redirected
- **WHEN** a non-admin visits /admin/coaching
- **THEN** the system SHALL redirect to the main page (/)

### Requirement: Admin-only API for analysis results
The system SHALL provide GET /admin/analysis/results accepting optional query param run_id. Returns the latest completed run's operator_digests and conversation_assessments. Only admin users SHALL access this endpoint.

#### Scenario: Fetch latest results
- **WHEN** admin sends GET /admin/analysis/results without run_id
- **THEN** the system SHALL return the most recent completed analysis run with its operator_digests and aggregated salvageable_sales

#### Scenario: Fetch specific run
- **WHEN** admin sends GET /admin/analysis/results?run_id=5
- **THEN** the system SHALL return results for that specific run

#### Scenario: Run still in progress
- **WHEN** admin fetches results for a run with status="running"
- **THEN** the system SHALL return partial results (assessments completed so far) with status="running" indicator

### Requirement: Analysis processes conversations with outbound activity in period
The analysis SHALL select conversations that had at least one outbound message (direction='outbound') with created_at within the analysis period. Conversations with only inbound messages in the period (client messaged but no one responded) SHALL be flagged separately as "sem resposta".

#### Scenario: Active conversations selected
- **WHEN** the analysis runs for a period
- **THEN** it SHALL query conversations with outbound messages in the period
- **THEN** each conversation SHALL be processed with its FULL message history (not just the period), to give the LLM complete context

#### Scenario: Unanswered conversations flagged
- **WHEN** a conversation has inbound messages in the period but no outbound messages
- **THEN** it SHALL appear in a separate "sem_resposta" list in the results with conversation_id, contact_name, last_inbound_message, and hours_waiting

### Requirement: Concurrency control for LLM calls
The analysis SHALL process conversations with limited concurrency (max 5 concurrent LLM calls) to avoid rate limiting and excessive cost. Progress SHALL be trackable.

#### Scenario: Batch processing
- **WHEN** the analysis processes 30 conversations
- **THEN** at most 5 LLM calls SHALL be active simultaneously (using asyncio.Semaphore)
- **THEN** after all conversation assessments are done, operator digests SHALL be generated sequentially (one per operator)

### Requirement: Direct tone for admin-only reports
The LLM prompts for both conversation assessment and operator digest SHALL use direct, undiplomatic language. The reports are internal management tools, not operator-facing feedback.

#### Scenario: Tone calibration
- **WHEN** the system builds prompts for analysis
- **THEN** the system prompt SHALL instruct the LLM to be direct: "Este relatorio e interno, so o gestor ve. Seja direto. Nomeie problemas sem eufemismo. 'Piloto automatico', 'resposta preguicosa', 'perdeu a venda' sao termos aceitaveis quando adequados."
