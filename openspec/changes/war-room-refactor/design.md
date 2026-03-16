## Context

O CaioWoot é um app FastAPI com SQLite + ChromaDB, frontend vanilla JS modularizado em ES modules. Ferramenta interna com poucos operadores. Os problemas foram identificados por uma war room com 4 especialistas e consolidados em `openspec/war-room-report.md`.

O refactor está dividido em 6 blocos por prioridade. Os blocos são independentes entre si e podem ser implementados em qualquer ordem, embora a sequência proposta minimize riscos.

## Goals / Non-Goals

**Goals:**
- Eliminar os 3 problemas mais graves de engenharia (conexões DB, duplicação de envio, migrations silenciosas)
- Adicionar infraestrutura mínima de deploy (Docker) e operação (health check, backup)
- Melhorar a experiência do operador nos pontos de maior fricção (loading states, auto-select viés, alerts)
- Decompor o god module draft_engine.py
- Corrigir inconsistências no design system e acessibilidade básica

**Non-Goals:**
- Migrar para PostgreSQL ou outro RDBMS
- Introduzir framework frontend (React, Vue, etc.)
- Adicionar structured logging, métricas ou tracing
- Implementar WebSocket channels
- Adicionar CI/CD
- Introduzir repository pattern

## Decisions

### DB Injection via FastAPI Depends

```python
# database.py
async def get_db_connection():
    db = await aiosqlite.connect(settings.database_path)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()

# PRAGMAs executados uma vez no startup (init_db), não a cada conexão
```

Routes recebem `db: aiosqlite.Connection = Depends(get_db_connection)`. Services recebem `db` como parâmetro. Isso elimina:
- Os 16 patches de get_db no conftest (substituídos por app.dependency_overrides)
- PRAGMAs desnecessários a cada conexão
- Risco de leak por `finally: close()` manual esquecido

### Unificação do fluxo de envio

Criar `app/services/message_sender.py` com uma única função:

```python
async def send_and_record(
    db, conv_id, text, draft_id=None, draft_group_id=None,
    selected_draft_index=None, operator_instruction=None,
    regeneration_count=0, file=None, filename=None
) -> dict:
    # 1. Enviar via Evolution API (texto ou com arquivo)
    # 2. Inserir mensagem no DB
    # 3. Registrar edit_pair se tinha draft
    # 4. Marcar drafts como sent/discarded
    # 5. Disparar generate_annotation em background
    # 6. Broadcast WebSocket
    # 7. Retornar mensagem criada
```

O handler de `messages.py` e `send_executor.py` delegam para esta função. A duplicação de ~80 linhas é eliminada.

### Decomposição do draft_engine.py

Separar em 3 módulos:

```
app/services/
  prompt_builder.py    ← _build_system_prompt, _build_conversation_history,
                         _get_approach_modifiers, _build_fewshot_*
  claude_client.py     ← singleton AsyncAnthropic, _call_haiku
  draft_engine.py      ← generate_drafts, regenerate_draft (orquestração)
```

Unificar `generate_drafts` e `regenerate_draft` extraindo a lógica comum para um método privado `_generate_draft_group()`. As diferenças (criar vs atualizar/deletar drafts) ficam nos wrappers públicos.

### Singletons para HTTP clients

```python
# app/services/claude_client.py
_client = None
def get_anthropic_client():
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client

# app/services/evolution.py
_http_client = None
def get_evolution_client():
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30)
    return _http_client
```

### Toast system no frontend

Criar `js/ui/toast.js` com API simples:

```javascript
export function showToast(message, type = 'info', duration = 3000) { ... }
export function showConfirm(message, onConfirm) { ... }
```

Estilo visual: pill flutuante no topo da tela, desaparece após timeout. Tipos: info (cinza), success (verde), error (vermelho). O confirm mostra modal leve com 2 botões.

CSS em `css/toast.css`. Substituir todas as 12+ chamadas de `alert()` e `confirm()`.

### Loading state para drafts

Quando mensagem inbound chega via WebSocket, mostrar skeleton no `#draft-cards-container` antes dos drafts serem gerados. O skeleton desaparece quando `drafts_ready` chega via WS.

Remover o auto-select do primeiro draft em `showDrafts()`. Os 3 cards aparecem sem seleção. O textarea fica vazio com placeholder "Selecione um draft acima para editar". O operador clica conscientemente.

### Indicador de conexão WebSocket

Dot no `#sidebar-header`: verde quando WS está OPEN, vermelho quando CLOSED/ERROR. Atualizado pelos event handlers do WebSocket em `ws.js`.

### Docker

```dockerfile
FROM python:3.12-slim
RUN pip install uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
COPY . .
EXPOSE 8002
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
```

```yaml
# docker-compose.yml
services:
  caiowoot:
    build: .
    ports: ["8002:8002"]
    volumes:
      - ./data:/app/data
      - ./knowledge:/app/knowledge
    env_file: .env
    restart: unless-stopped
```

### Backup SQLite

Script `scripts/backup.sh`:
```bash
#!/bin/bash
sqlite3 data/caiowoot.db ".backup data/backup-$(date +%Y%m%d-%H%M%S).db"
find data/ -name "backup-*.db" -mtime +7 -delete
```

Executável via cron: `0 */6 * * * /path/to/scripts/backup.sh`

## Risks / Trade-offs

**DB injection refactor é o mais arriscado.** Toca virtualmente todos os módulos do backend e os testes. Deve ser feito num commit atômico com todos os testes passando. Abordagem: criar a nova `get_db_connection` generator, atualizar routes com Depends, atualizar services para receber db como param, atualizar conftest com dependency_overrides, rodar testes, deletar o get_db antigo.

**Decomposição do draft_engine pode quebrar a prompt caching.** O fluxo atual de construção do prompt é monolítico justamente porque a ordem dos blocos afeta o cache_control ephemeral. Ao separar em prompt_builder.py, garantir que a interface retorna o prompt na mesma estrutura.

**Remover auto-select pode irritar inicialmente.** Operadores acostumados ao fluxo atual (draft já no textarea) vão precisar de um clique extra. O ganho no learning loop justifica a mudança.
