# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is CaioWoot

Copiloto de vendas para WhatsApp. Recebe mensagens de clientes via Evolution API, gera 3 variações de resposta (direta, consultiva, casual) usando Claude Haiku em paralelo, e apresenta numa interface web para o operador revisar, editar e enviar. Cada interação alimenta um loop de aprendizado contínuo.

## Commands

```bash
# Dev server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# All tests
uv run pytest tests/ -v

# Single test file
uv run pytest tests/test_draft_engine.py -v

# Single test
uv run pytest tests/test_draft_engine.py::test_name -v

# Install/sync deps
uv sync
```

## Architecture

### Request flow

1. Evolution API webhook → `POST /webhook` → insere mensagem → dispara `generate_drafts()` como `asyncio.create_task`
2. `draft_engine.generate_drafts()` gera 3 variações em paralelo via `asyncio.gather` chamando Claude Haiku com approaches diferentes (direta, consultiva, casual)
3. Drafts prontos → broadcast via WebSocket para todos os clientes conectados
4. Operador seleciona/edita/envia → `POST /conversations/{id}/send` → envia via Evolution API → registra edit_pair

### Learning loop (continuous learning)

O sistema aprende com as edições do operador em 4 estágios:

1. **Edit pairs**: toda mensagem enviada com draft registra (original_draft, final_message, was_edited) em `edit_pairs`
2. **Strategic annotation**: `generate_annotation()` roda em background após envio, gerando uma anotação sobre a decisão estratégica do operador (via Haiku). Salva em `edit_pairs.strategic_annotation`
3. **ChromaDB indexing**: `smart_retrieval.index_edit_pair()` indexa o `situation_summary` no ChromaDB para busca por similaridade
4. **Smart retrieval**: na próxima geração de draft, `retrieve_similar()` busca edit_pairs com situações parecidas para montar few-shot examples no prompt. Prioriza pares validados pelo operador

Além disso:
- **Situation summary**: gerado por Haiku antes dos drafts, descreve estágio da conversa e perfil do cliente
- **Learned rules**: operador pode promover anotações a regras permanentes, injetadas no system prompt
- **Review UI** (`/review`): operador valida, rejeita ou promove anotações estratégicas

### Key modules

- `app/services/draft_engine.py` — coração do sistema. Monta prompt completo (knowledge + few-shot + rules + temporal context + attachments), chama Haiku 3x em paralelo, salva drafts
- `app/services/smart_retrieval.py` — ChromaDB wrapper. Indexa e busca edit_pairs por similaridade de situação
- `app/services/situation_summary.py` — gera resumo estratégico da conversa antes dos drafts
- `app/services/strategic_annotation.py` — gera anotação pós-envio sobre decisão do operador
- `app/services/evolution.py` — integração com Evolution API (sendText, sendMedia, sendDocument)
- `app/services/knowledge.py` — carrega e cacheia markdown de `knowledge/*.md`
- `app/services/learned_rules.py` — CRUD de regras aprendidas (SQLite)
- `app/database.py` — schema SQLite + migrations + ChromaDB client singleton
- `app/auth.py` — middleware de auth (session cookie via itsdangerous), rate limiting, operator identity

### Database

SQLite com WAL mode via aiosqlite. Migrations manuais em `database.py:MIGRATIONS` (lista de tuples nome+SQL). ChromaDB persistente em `data/chroma/` para embeddings de situações.

Tabelas principais: `conversations`, `messages`, `drafts`, `edit_pairs`, `learned_rules`, `_migrations`.

### Frontend

Vanilla HTML/JS em `app/static/`. Sem framework. WebSocket para real-time updates. PWA com manifest.json e service worker básico.

### Data directories

- `data/caiowoot.db` — SQLite principal
- `data/chroma/` — ChromaDB persistente
- `data/prompts/` — prompts salvos em disco com hash SHA-256
- `data/attachments/` — arquivos enviados pelo operador
- `knowledge/*.md` — base de conhecimento dos cursos (hot-reload por mtime)
- `knowledge/attachments/` — PDFs para sugestão de envio ao cliente

## Testing patterns

Tests usam `pytest-asyncio` com SQLite `:memory:`. O `conftest.py` define:

- `NonClosingConnection` wrapper para compartilhar conexão entre test e app
- Patches extensivos em `get_db` de cada módulo que importa direto (webhook, conversations, messages, review, draft_engine, learned_rules)
- Mocks de `generate_situation_summary`, `retrieve_similar`, `get_active_rules`, `save_prompt`, `websocket_manager`
- `mock_claude_api` e `mock_evolution_api` como fixtures reutilizáveis
- `make_webhook_payload()` helper para simular webhooks da Evolution API

Para adicionar um teste que precisa de DB, use a fixture `db` (que já aplica todos os patches) e `client` (httpx AsyncClient com ASGI transport).
