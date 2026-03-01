## 1. Database & Dependencies

- [x] 1.1 Add `chromadb` to pyproject.toml dependencies
- [x] 1.2 Add migration: new columns `situation_summary`, `strategic_annotation`, `validated`, `rejected` to edit_pairs table
- [x] 1.3 Add migration: new column `situation_summary` to drafts table
- [x] 1.4 Create `learned_rules` table (id, rule_text, source_edit_pair_id, is_active, created_at, updated_at)
- [x] 1.5 Initialize ChromaDB collection ("situations") in app startup (init_db or similar)

## 2. Situation Summary

- [x] 2.1 Create `app/services/situation_summary.py` with function to generate situation summary via Haiku (input: conversation history + contact name, output: 2-3 sentence summary)
- [x] 2.2 Write tests for situation summary generation (mock Haiku call, verify prompt structure)

## 3. Smart Retrieval

- [x] 3.1 Create `app/services/smart_retrieval.py` with ChromaDB wrapper: index_edit_pair(edit_pair_id, situation_summary, metadata) and retrieve_similar(situation_summary, k=5)
- [x] 3.2 Implement prioritized retrieval: search validated pairs first, fill remaining slots from non-validated
- [x] 3.3 Implement rebuild_index() function that recreates ChromaDB from all edit_pairs with situation_summary in SQLite
- [x] 3.4 Write tests for retrieval (mock ChromaDB, verify priority logic and cold start fallback)

## 4. Learned Rules

- [x] 4.1 Create `app/services/learned_rules.py` with functions: get_active_rules(), create_rule(), update_rule(), toggle_rule()
- [x] 4.2 Create `app/routes/rules.py` with API endpoints: GET /rules, POST /rules, PUT /rules/{id}, PATCH /rules/{id}/toggle
- [x] 4.3 Write tests for rules CRUD and toggle

## 5. Draft Engine Refactor

- [x] 5.1 Refactor `_build_prompt_parts` to call situation summary generation first
- [x] 5.2 Replace chronological edit pair retrieval with smart_retrieval.retrieve_similar()
- [x] 5.3 Build enriched few-shot format: include situation_summary + strategic_annotation alongside customer_message, draft, final_message
- [x] 5.4 Inject active learned rules into system prompt section "## Regras aprendidas"
- [x] 5.5 Include situation summary in prompt as "## Situação atual" section
- [x] 5.6 Save situation_summary to drafts table on generation
- [x] 5.7 Update send_message route to save situation_summary from draft group into edit pair
- [x] 5.8 Write tests for refactored draft engine (verify prompt structure includes summary, retrieval results, and rules)

## 6. Strategic Annotation

- [x] 6.1 Create `app/services/strategic_annotation.py` with function to analyze diff (draft vs final_message) and generate annotation via Haiku
- [x] 6.2 Wire annotation as background task in send_message route (asyncio.create_task after edit pair insert)
- [x] 6.3 After annotation is generated, index the edit pair in ChromaDB (smart_retrieval.index_edit_pair)
- [x] 6.4 Write tests for annotation generation (mock Haiku, verify edited vs non-edited scenarios, verify failure is non-blocking)

## 7. Learning Review API

- [x] 7.1 Create `app/routes/review.py` with GET /review (list pending annotations with stats)
- [x] 7.2 Add POST /review/{edit_pair_id}/validate (mark as validated, update ChromaDB metadata)
- [x] 7.3 Add POST /review/{edit_pair_id}/reject (mark as validated+rejected, update ChromaDB metadata)
- [x] 7.4 Add POST /review/{edit_pair_id}/promote (create learned rule from annotation, mark as validated)
- [x] 7.5 Write tests for review endpoints

## 8. Frontend - Review UI

- [x] 8.1 Add review page route and basic layout (list of pending annotations)
- [x] 8.2 Implement annotation card component (shows situation, customer msg, draft vs final, annotation text)
- [x] 8.3 Add OK / Errado / Promover actions with API calls
- [x] 8.4 Add rule text editing on promote (inline edit before confirming)
- [x] 8.5 Add review stats summary (total pending, edited, confirmed)
- [x] 8.6 Add navigation link to review page from main inbox
