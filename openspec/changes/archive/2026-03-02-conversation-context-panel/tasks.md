## 1. Database

- [x] 1.1 Add `funnel_product TEXT` and `funnel_stage TEXT` columns to `conversations` in SCHEMA and MIGRATIONS

## 2. Situation Summary (structured output)

- [x] 2.1 Update `generate_situation_summary()` prompt to request JSON with `summary`, `product`, `stage` fields
- [x] 2.2 Update `generate_situation_summary()` to parse JSON response, with graceful fallback to text-only on parse failure
- [x] 2.3 Update `draft_engine._build_prompt_parts()` to consume structured summary and UPDATE conversation funnel fields

## 3. Backend API

- [x] 3.1 Add `funnel_product` and `funnel_stage` to `GET /conversations` query
- [x] 3.2 Add `funnel_product`, `funnel_stage`, and latest `situation_summary` to `GET /conversations/{id}` response
- [x] 3.3 Add `PATCH /conversations/{id}/funnel` endpoint with stage validation

## 4. Frontend - Context Panel

- [x] 4.1 Add `#context-panel` HTML structure in `index.html` (product dropdown, stage stepper, summary block)
- [x] 4.2 Add CSS for context panel layout (280px right panel, hidden on mobile)
- [x] 4.3 Add product dropdown with known products from knowledge files
- [x] 4.4 Add funnel stage stepper/radio with visual progression
- [x] 4.5 Add JS to render context panel on `openConversation()` and handle product/stage changes via PATCH

## 5. Tests

- [x] 5.1 Test: `generate_situation_summary()` returns structured JSON with product and stage
- [x] 5.2 Test: `generate_situation_summary()` graceful fallback when JSON parse fails
- [x] 5.3 Test: draft generation updates conversation funnel fields
- [x] 5.4 Test: `PATCH /conversations/{id}/funnel` updates fields
- [x] 5.5 Test: `PATCH /conversations/{id}/funnel` rejects invalid stage
- [x] 5.6 Test: `GET /conversations` includes funnel_product and funnel_stage
- [x] 5.7 Test: `GET /conversations/{id}` includes funnel data and situation_summary
