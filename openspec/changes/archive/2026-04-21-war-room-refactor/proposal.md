## Why

O CaioWoot evoluiu organicamente de protótipo para ferramenta de produção. Uma war room com 4 especialistas (Arquitetura, QA, DevOps, Design) identificou 26 problemas acionáveis. Os conceitos core estão sólidos (learning loop, 3 drafts, annotation pipeline), mas a engenharia acumulou dívida técnica em gestão de conexões, duplicação de código, ausência de feedback ao operador, e infraestrutura de deploy inexistente. Este refactor resolve os problemas que causam bugs, impedem manutenção, ou degradam a experiência do operador.

## What Changes

### Fundação (CRÍTICO)
- Adicionar `Pillow` ao `pyproject.toml`
- Corrigir `except: pass` nas migrations para tratar apenas `OperationalError` de "already exists"
- Criar `Dockerfile` + `docker-compose.yml` com restart policy
- Refatorar `get_db()` para dependency injection via FastAPI `Depends()`, eliminando 16 patches no conftest

### Backend (ALTO)
- Unificar lógica de envio duplicada entre `messages.py` e `send_executor.py`
- Sincronizar `SCHEMA` com `MIGRATIONS` (incluir tabelas faltantes)
- Criar singletons para `anthropic.AsyncAnthropic` e `httpx.AsyncClient`
- Substituir `datetime.utcnow()` por `datetime.now(timezone.utc)`
- Adicionar health check endpoint `GET /health`
- Adicionar backup automatizado do SQLite

### Frontend UX (ALTO)
- Adicionar loading state para geração de drafts
- Remover auto-select do primeiro draft (evitar viés no learning loop)
- Adicionar indicador de status de conexão WebSocket
- Substituir `alert()`/`confirm()` por toast/snackbar system
- Adicionar feedback de envio no botão e toast de confirmação

### Qualidade de código (MÉDIO)
- Decompor `draft_engine.py` (650 linhas) em módulos menores
- Migrar inline styles de `campaigns.js` para CSS com tokens
- Corrigir `event.target` global em `generateVariations`
- Corrigir `--space-xxl` e consolidar tokens de cor

### Mobile e Acessibilidade (MÉDIO)
- Mostrar texto dos drafts nos pills mobile
- Adicionar acesso ao context-panel no mobile
- Adicionar testes para error paths do draft_engine
- Adicionar `aria-label` em botões com ícone
- Corrigir contraste dos cinzas (WCAG 4.5:1)

### Polish (BAIXO)
- Adicionar índices no banco para queries frequentes
- Adicionar busca/filtro na sidebar
- Adicionar tokens de tipografia e transition
- Webhook validation

## Capabilities

### New Capabilities
- `db-injection`: Dependency injection de conexão DB via FastAPI Depends, eliminando get_db() direto
- `unified-send`: Service unificado de envio de mensagem (texto + arquivo) com edit_pair
- `docker-deploy`: Dockerfile + docker-compose para deploy reprodutível com restart
- `health-check`: Endpoint de health check com verificação de DB e background tasks
- `toast-system`: Componente frontend de toast/snackbar substituindo alert/confirm nativos
- `draft-loading`: Loading states e remoção de auto-select na geração de drafts
- `ws-status`: Indicador visual de status de conexão WebSocket

### Modified Capabilities
- `draft-engine`: Decomposição em módulos (prompt builder, claude caller, draft persistence)
- `webhook-receiver`: Validação de origem da Evolution API

## Impact

- **Backend:** database.py, send_executor.py, messages.py, draft_engine.py, evolution.py, scheduler.py, campaign_executor.py, main.py, config.py
- **Frontend:** js/ui/drafts.js, js/ui/compose.js, js/ui/campaigns.js, js/main.js, js/ws.js, css/tokens.css, css/campaigns.css, index.html
- **Testes:** conftest.py (eliminação dos 16 patches), novos testes de error paths
- **Infra:** novo Dockerfile, docker-compose.yml, script de backup
- **Deps:** pyproject.toml (Pillow)
