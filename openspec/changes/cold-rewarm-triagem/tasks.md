## Schema

- [ ] Migration `cold_dispatches_table` em `app/database.py`:
  - id, conversation_id FK, classification (TEXT), confidence (TEXT: high/med/low), quote_from_lead (TEXT), action (TEXT: mentoria/conteudo/skip), message_draft (TEXT), message_sent (TEXT), scheduled_send_id FK nullable, status (previewed/approved/sent/skipped/failed), responded_at TIMESTAMP, created_at TIMESTAMP.
  - Index em (conversation_id, created_at) pra cooldown query.
  - Index em (action, created_at) pra contagem mensal de mentoria.
- [ ] Migration `cold_do_not_contact_on_conversations`: ALTER conversations ADD COLUMN cold_do_not_contact INTEGER DEFAULT 0.
- [ ] Espelha no SCHEMA (bootstrap) pra testes.

## Config

- [ ] `cold_mentoria_monthly_cap: int = 15` em `app/config.py` Settings.

## Service `app/services/cold_triage.py`

- [ ] `COLD_CLASSIFY_TOOL` e `COLD_CLASSIFY_SYSTEM_PROMPT`: tool com `classification` (enum: objecao_preco/objecao_timing/objecao_conteudo/tire_kicker/negativo_explicito/perdido_no_ruido/nao_classificavel), `confidence` (enum: high/med/low), `quote_from_lead` (str), `reasoning` (str).
- [ ] `COLD_COMPOSE_TOOL` e `COLD_COMPOSE_SYSTEM_PROMPT`: tool com `message` (str). Prompt instrui tom Caio (minúsculas, sem em-dash, primeira pessoa, citação literal, fat-finger ocasional, sem brincadeira forçada).
- [ ] `select_cold_candidates(db, limit=80) -> list[dict]`:
  - funnel_product='curso-cdo'
  - funnel_stage em (handbook_sent, link_sent)
  - última mensagem inbound > 30 dias atrás
  - não comprou (funnel_stage não é estado terminal)
  - cold_do_not_contact = 0
  - não tem cold_dispatches criado nos últimos 90 dias
  - ORDER BY funnel_stage DESC (link_sent antes), last_inbound_at DESC (mais frescos antes)
- [ ] `classify_conversation(conv_id, db=None) -> dict`: Haiku com `COLD_CLASSIFY_TOOL`. Retorna dict normalizado. Se Haiku falhar ou confidence=low, retorna classification='nao_classificavel' e force skip na matriz.
- [ ] `count_mentoria_offers_this_month(db) -> int`: COUNT em cold_dispatches WHERE action='mentoria' AND status IN ('sent','approved') AND created_at >= início do mês local.
- [ ] `apply_matrix(classification, stage, mentoria_used, cap) -> str`: retorna 'mentoria' | 'conteudo' | 'skip'. Tabela embutida. low confidence → skip.
- [ ] `compose_message(conv_id, action, classification, quote, contact_name) -> str`: Haiku com `COLD_COMPOSE_TOOL`. Inclui instrução explícita do quote a citar.
- [ ] `score_candidate(classification, stage, days_cold) -> float`: função de priorização.
- [ ] `async def run_preview(db, limit=20) -> list[dict]`: pipeline completo, grava `cold_dispatches` com status='previewed', retorna items pro modal.
- [ ] `async def execute_batch(items, db=None)`: rate-limited sender igual run_batch do D-1 mas atualiza `cold_dispatches` ao final.

## Routes `app/routes/cold_rewarm.py`

- [ ] `POST /cold-rewarm/preview`: chama `run_preview`, retorna JSON array com `{item_id, dispatch_id, conversation_id, phone_number, contact_name, funnel_stage, classification, confidence, quote_from_lead, action, message, message_reason}`. Items com action=skip em seção separada.
- [ ] `POST /cold-rewarm/execute`: recebe `{items: [{dispatch_id, message}]}`, dispara background task `execute_batch`, retorna 202.

## Frontend

- [ ] `app/static/js/ui/cold_rewarm.js`: clone estruturado de `rewarm.js`, renderiza campos extras (classification chip, quote quote, action badge).
- [ ] `app/static/css/cold_rewarm.css`: estilos específicos (chips, ação, citação).
- [ ] Botão em `app/static/index.html` ao lado do "Reesquentar D-1": `<button id="cold-rewarm-btn" onclick="startColdRewarm()">Cold Rewarm</button>`.
- [ ] Modal `cold-rewarm-modal` em index.html, estrutura idêntica ao `rewarm-modal`.
- [ ] Export funções em `app/static/js/main.js` ou equivalente se o padrão exigir.

## Wiring

- [ ] `app/main.py`: include router `cold_rewarm`.
- [ ] `app/routes/webhook.py`: hook existente `handle_reward_inbound` precisa também marcar cold_dispatches.responded_at quando inbound chegar em conv com cold_dispatch recente. Adicionar função paralela `mark_cold_response_received` ou estender.
- [ ] `tests/conftest.py`: adicionar patches `app.services.cold_triage.get_db` e `app.routes.cold_rewarm.get_db`.

## Testes (TDD)

Ver `tests.md` para cenários detalhados. Arquivos:

- [ ] `tests/test_cold_triage_classify.py`: classificação (mock Haiku, cada label, low confidence força skip).
- [ ] `tests/test_cold_triage_matrix.py`: cada célula da matriz (estágio × classificação → ação), cap consumido, cap zerado.
- [ ] `tests/test_cold_triage_candidates.py`: seleção respeita filtros (+30d, sem negativa, fora do cooldown, cold_do_not_contact).
- [ ] `tests/test_cold_triage_compose.py`: compositor produz string, recebe quote no prompt, retorna fallback se Haiku vazio.
- [ ] `tests/test_cold_rewarm_routes.py`: preview 200 + execute 202, edição de mensagem no execute preservada em message_sent.
- [ ] `tests/test_cold_rewarm_cooldown.py`: conversa com cold_dispatch <90d não volta ao pool.
- [ ] `tests/test_cold_reward_hook.py`: inbound em conv com cold_dispatch recente marca responded_at.

## Qualidade

- [ ] `uv run pytest tests/ -q` tudo verde (inclui rewarm e bandit existentes).
- [ ] Rodar `uv run uvicorn` local, clicar botão, validar modal e disparo manual com 1-2 conversas de teste.
- [ ] Após 1 batch real (20 envios), revisar `cold_dispatches` e ajustar prompts se classificações tiverem desvio.
