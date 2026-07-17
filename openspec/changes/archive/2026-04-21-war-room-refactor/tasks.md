## 1. Fundação (CRÍTICO)

- [x] 1.1 Adicionar `Pillow` ao `pyproject.toml` e rodar `uv sync`
- [x] 1.2 Corrigir `except: pass` em `database.py` `_run_migrations` para capturar apenas `OperationalError` com mensagem "already exists" ou "duplicate column"; logar e re-raise qualquer outro erro
- [x] 1.3 Criar `Dockerfile` (python:3.12-slim + uv) e `docker-compose.yml` (volume data/ e knowledge/, env_file, restart unless-stopped, porta 8002)
- [x] 1.4 Criar `get_db_connection` async generator em `database.py` que usa `yield` e fecha no finally
- [x] 1.5 Mover PRAGMAs (WAL, foreign_keys) para `init_db()` (executar uma vez no startup)
- [x] 1.6 Atualizar TODAS as routes para receber `db: aiosqlite.Connection = Depends(get_db_connection)` em vez de chamar `get_db()` manualmente
- [x] 1.7 Atualizar TODOS os services para receber `db` como parâmetro em vez de importar e chamar `get_db()`
- [x] 1.8 Atualizar `conftest.py`: substituir os 16 patches de `get_db` por `app.dependency_overrides[get_db_connection]`
- [x] 1.9 Rodar `uv run pytest tests/ -v` e garantir que todos os testes passam

## 2. Backend (ALTO)

- [x] 2.1 Criar `app/services/message_sender.py` com função `send_and_record()` unificando a lógica de `messages.py` (file send) e `send_executor.py` (text send)
- [x] 2.2 Refatorar `app/routes/messages.py` para delegar ao `message_sender.send_and_record()`
- [x] 2.3 Refatorar `app/services/send_executor.py` para delegar ao `message_sender.send_and_record()`
- [x] 2.4 Sincronizar SCHEMA em `database.py` para incluir tabelas `analysis_runs`, `conversation_assessments`, `operator_digests`
- [x] 2.5 Criar singleton `get_anthropic_client()` em `app/services/claude_client.py`
- [x] 2.6 Criar singleton `get_evolution_client()` em `app/services/evolution.py` (httpx.AsyncClient reutilizado)
- [x] 2.7 Atualizar `draft_engine.py`, `situation_summary.py`, `strategic_annotation.py`, `campaign_variations.py`, `conversation_analysis.py` para usar o singleton Anthropic
- [x] 2.8 Atualizar `evolution.py` send functions para usar o singleton httpx client
- [x] 2.9 Substituir `datetime.utcnow()` por `datetime.now(timezone.utc)` em `send_executor.py` e qualquer outro ponto
- [x] 2.10 Adicionar endpoint `GET /health` que retorna status do DB (SELECT 1) e das background tasks
- [x] 2.11 Criar `scripts/backup.sh` com sqlite3 .backup + cleanup de backups > 7 dias

## 3. Frontend UX (ALTO)

- [x] 3.1 Adicionar skeleton/spinner no `#draft-cards-container` quando mensagem inbound chega (antes dos drafts serem gerados)
- [x] 3.2 Remover auto-select do primeiro draft em `showDrafts()` — mostrar 3 cards sem pré-seleção
- [x] 3.3 Atualizar textarea placeholder para "Selecione um draft acima para editar" quando nenhum draft está selecionado
- [x] 3.4 Criar `js/ui/toast.js` com `showToast(message, type, duration)` e `showConfirm(message, onConfirm)`
- [x] 3.5 Criar `css/toast.css` com estilos para pill flutuante e modal de confirmação
- [x] 3.6 Substituir todas as chamadas de `alert()` por `showToast()` (compose.js, campaigns.js, knowledge.js, schedule.js)
- [x] 3.7 Substituir todas as chamadas de `confirm()` por `showConfirm()` (campaigns.js, knowledge.js)
- [x] 3.8 Adicionar "Enviando..." no send-btn durante envio e toast "Mensagem enviada" após sucesso
- [x] 3.9 Adicionar dot de status WS no sidebar-header (verde=OPEN, vermelho=CLOSED) em `ws.js`
- [x] 3.10 Adicionar link CSS do toast.css no index.html e import do toast.js no main.js

## 4. Qualidade de código (MÉDIO)

- [x] 4.1 Criar `app/services/prompt_builder.py` extraindo `_build_system_prompt`, `_build_conversation_history`, `_get_approach_modifiers`, `_build_fewshot_*` de `draft_engine.py`
- [x] 4.2 Mover `_call_haiku` para `app/services/claude_client.py` (junto com o singleton)
- [x] 4.3 Unificar `generate_drafts` e `regenerate_draft` via método compartilhado `_generate_draft_group()`
- [x] 4.4 Migrar inline styles de `campaigns.js` (botões de ação, variações, contatos) para classes CSS em `campaigns.css`
- [x] 4.5 Extrair `statusColors`/`statusLabels` duplicados em `campaigns.js` para constantes compartilhadas no topo do módulo
- [x] 4.6 Corrigir `event.target` global em `generateVariations` para receber event como parâmetro
- [x] 4.7 Corrigir `--space-xxl: 20px` para `32px` em `tokens.css`
- [x] 4.8 Consolidar tokens de cor cinza: remover `--color-text-faint` (= placeholder), unificar em 4 níveis (text, secondary, muted, disabled)

## 5. Mobile e Acessibilidade (MÉDIO)

- [x] 5.1 Mobile: mostrar 1-2 linhas do texto do draft nos pills (não só o label) via CSS/JS ajuste
- [x] 5.2 Mobile: adicionar botão/drawer para acessar context-panel
- [x] 5.3 Adicionar testes para error path do draft_engine: quando Claude API retorna erro, verificar que fallback text é salvo e broadcasted
- [x] 5.4 Adicionar `aria-label` em todos os botões com ícone: hamburger, gear, regen-all, regen-instruction, attach, close, clear-draft
- [x] 5.5 Corrigir contraste: `--color-text-light` de #999 para #767676, `--color-text-muted` de #888 para #595959

## 6. Polish (BAIXO)

- [x] 6.1 Adicionar índices: `CREATE INDEX idx_messages_conv ON messages(conversation_id)`, `idx_drafts_conv_status ON drafts(conversation_id, status)`, `idx_edit_pairs_conv ON edit_pairs(conversation_id)`, `idx_campaign_contacts_camp_status ON campaign_contacts(campaign_id, status)`
- [x] 6.2 Adicionar busca/filtro na sidebar de conversas (input de texto que filtra por nome/telefone)
- [x] 6.3 Adicionar tokens de tipografia (`--font-size-xs: 11px`, `--font-size-sm: 12px`, `--font-size-md: 13px`, `--font-size-base: 14px`, `--font-size-lg: 16px`)
- [x] 6.4 Adicionar tokens de transition (`--transition-fast: 0.2s`, `--transition-normal: 0.3s`)
- [x] 6.5 Webhook validation: ler header `x-evolution-token` e comparar com `EVOLUTION_WEBHOOK_SECRET` se configurado
