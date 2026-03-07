## 1. Database

- [x] 1.1 Add migrations for analysis_runs, conversation_assessments, and operator_digests tables to MIGRATIONS list in app/database.py

## 2. Conversation Analysis Service

- [x] 2.1 Create app/services/conversation_analysis.py with analyze_conversation() function: collects messages, edit_pairs, computes metrics (draft acceptance rate, response times, approach distribution), builds LLM prompt with knowledge base and conversation context, calls Haiku, returns structured assessment JSON
- [x] 2.2 Write prompt for conversation analysis: system prompt with knowledge base + cache_control, user prompt with conversation messages, edit_pair data, computed metrics, instructions for factual checking, engagement assessment, sale status classification, and direct tone directive

## 3. Operator Coaching Service

- [x] 3.1 Create app/services/operator_coaching.py with run_analysis() orchestrator: creates analysis_run record, queries conversations with outbound activity in period, processes each via analyze_conversation() with asyncio.Semaphore(5), groups assessments by operator, generates operator digest via Sonnet, flags unanswered conversations, updates run status on completion/failure
- [x] 3.2 Write prompt for operator digest: receives all conversation assessments + aggregated metrics for one operator, instructs Sonnet to identify behavioral patterns with concrete examples, generate salvageable sales list, use direct management tone

## 4. Admin Routes

- [x] 4.1 Create app/routes/admin.py with is_admin guard: POST /admin/analysis/run (trigger analysis with optional period, returns run_id), GET /admin/analysis/results (latest or specific run results with operator_digests + salvageable_sales + unanswered), GET /admin/analysis/status/{run_id} (progress tracking)
- [x] 4.2 Register admin router in app/main.py

## 5. Frontend

- [x] 5.1 Create app/static/coaching.html: admin-only page with date range picker + "Rodar analise" button, "Vendas para salvar" section (priority-ordered), per-operator sections (metrics, patterns with examples, factual issues), polling for run progress, link to conversation from each assessment

## 6. Tests

- [x] 6.1 Write tests for conversation_analysis: mock Haiku call, verify prompt includes knowledge base and edit_pair data, verify structured output parsing, verify factual error detection, verify pilot-mode detection when all was_edited=false
- [x] 6.2 Write tests for operator_coaching: mock analysis pipeline, verify run lifecycle (running → completed/failed), verify concurrency semaphore, verify operator digest aggregation, verify unanswered conversations detection
- [x] 6.3 Write tests for admin routes: verify is_admin guard (403 for non-admin), verify run trigger returns run_id, verify results endpoint returns latest run
