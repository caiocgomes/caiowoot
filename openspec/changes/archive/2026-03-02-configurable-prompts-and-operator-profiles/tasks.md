## 1. Database & Config

- [x] 1.1 Add `prompt_config` table to SCHEMA and MIGRATIONS in `database.py`
- [x] 1.2 Add `operator_profiles` table to SCHEMA and MIGRATIONS in `database.py`
- [x] 1.3 Add `admin_operator` setting to `config.py` with fallback to first operator in list
- [x] 1.4 Add `is_admin(operator_name)` helper to `auth.py`

## 2. Prompt Config Service

- [x] 2.1 Create `app/services/prompt_config.py` with hardcoded defaults dict for all 8 keys
- [x] 2.2 Implement `get_all_prompts()` that reads from DB with hardcoded fallback per key
- [x] 2.3 Implement `update_prompts(updates: dict)` that upserts key-value pairs
- [x] 2.4 Implement `reset_prompt(key)` that deletes key from DB (falls back to default)

## 3. Operator Profile Service

- [x] 3.1 Create `app/services/operator_profile.py` with get/upsert functions
- [x] 3.2 Implement `get_profile(operator_name)` returning display_name and context
- [x] 3.3 Implement `upsert_profile(operator_name, display_name, context)`

## 4. API Routes

- [x] 4.1 Create `app/routes/settings.py` with router
- [x] 4.2 Implement `GET /api/settings/prompts` (any authenticated operator)
- [x] 4.3 Implement `PUT /api/settings/prompts` (admin only, uses `is_admin` check)
- [x] 4.4 Implement `GET /api/settings/profile` (reads operator from cookie)
- [x] 4.5 Implement `PUT /api/settings/profile` (writes operator from cookie)
- [x] 4.6 Implement `GET /api/settings/is-admin`
- [x] 4.7 Register settings router in `app/main.py`

## 5. Draft Engine Refactor

- [x] 5.1 Refactor `draft_engine.py` to read postura/tom/regras from `prompt_config` instead of SYSTEM_PROMPT constant
- [x] 5.2 Refactor approach modifiers to read from `prompt_config` keys instead of APPROACH_MODIFIERS constant
- [x] 5.3 Add operator_name parameter to `generate_drafts()` and `regenerate_draft()`
- [x] 5.4 Add operator profile injection: read profile, build "Sobre quem está respondendo" section
- [x] 5.5 Make opening paragraph dynamic: use operator display_name instead of hardcoded "Caio"
- [x] 5.6 Refactor `situation_summary.py` to read prompt from `prompt_config` with fallback
- [x] 5.7 Refactor `strategic_annotation.py` to read prompt from `prompt_config` with fallback

## 6. Plumbing: Pass Operator Through

- [x] 6.1 Update `routes/webhook.py` to pass operator_name=None to `generate_drafts()` (webhook has no operator)
- [x] 6.2 Update `routes/messages.py` to pass operator_name from cookie to `regenerate_draft()` and `generate_drafts()`

## 7. Frontend: Settings UI

- [x] 7.1 Add settings gear button to header in `index.html`
- [x] 7.2 Build settings modal structure with tabbed interface (Prompts / Meu Perfil)
- [x] 7.3 Implement Prompts tab: fetch, render textareas, save, reset per section
- [x] 7.4 Implement Meu Perfil tab: fetch, render form (display_name + context textarea with placeholder), save
- [x] 7.5 Implement admin check on modal open: hide Prompts tab for non-admins

## 8. Tests

- [x] 8.1 Tests for `prompt_config` service (get with defaults, update, reset)
- [x] 8.2 Tests for `operator_profile` service (get empty, upsert, get populated)
- [x] 8.3 Tests for settings API routes (admin check, CRUD prompts, CRUD profile, 403 for non-admin)
- [x] 8.4 Tests for draft engine reading prompts from DB instead of constants
- [x] 8.5 Tests for draft engine injecting operator profile into prompt
- [x] 8.6 Tests for situation_summary and strategic_annotation reading configurable prompts
