## Why

O CaioWoot evoluiu organicamente de protótipo para ferramenta de produção. Uma war room com 4 especialistas (Arquitetura, QA, DevOps, Design) identificou 26 problemas acionáveis. Os conceitos core estão sólidos (learning loop, 3 drafts, annotation pipeline), mas a engenharia acumulou dívida técnica em gestão de conexões, duplicação de código, ausência de feedback ao operador, e infraestrutura de deploy inexistente. Este refactor resolve os problemas que causam bugs, impedem manutenção, ou degradam a experiência do operador.

## O que muda

### Bloco 1: Fundação (CRÍTICO)

- Adicionar `Pillow` ao `pyproject.toml` (campanhas com imagem quebram em instalação limpa)
- Corrigir `except: pass` nas migrations para tratar apenas `OperationalError` de "already exists"; logar e re-raise qualquer outro erro
- Criar `Dockerfile` + `docker-compose.yml` com volume para `data/` e `knowledge/`, restart policy `unless-stopped`
- Refatorar `get_db()` para dependency injection via FastAPI `Depends()`: uma conexão por request, injetada automaticamente, fechada pelo framework. Elimina os 16 patches manuais no conftest

### Bloco 2: Backend (ALTO)

- Unificar lógica de envio duplicada entre `messages.py` (file path) e `send_executor.py` (text path) em um único service method
- Sincronizar `SCHEMA` com `MIGRATIONS`: incluir tabelas de `analysis_runs`, `conversation_assessments`, `operator_digests` no schema base
- Criar singletons para `anthropic.AsyncAnthropic` e `httpx.AsyncClient` (Evolution API) em vez de instanciar a cada chamada
- Substituir `datetime.utcnow()` por `datetime.now(timezone.utc)` em todos os pontos
- Adicionar health check endpoint `GET /health` (verifica DB + background tasks ativas)
- Adicionar backup automatizado do SQLite via script com `.backup`

### Bloco 3: Frontend UX (ALTO)

- Adicionar loading state (skeleton/spinner) no container de drafts enquanto aguarda geração
- Remover auto-select do primeiro draft: mostrar os 3 cards sem pré-selecionar nenhum, preencher textarea só quando operador clicar
- Adicionar indicador de status de conexão WebSocket (dot verde/vermelho no header)
- Substituir todos os `alert()`/`confirm()` (12+ ocorrências) por componente de toast/snackbar próprio
- Adicionar feedback de envio ("Enviando..." no botão, toast "Mensagem enviada" após sucesso)

### Bloco 4: Qualidade de código (MÉDIO)

- Decompor `draft_engine.py` (650 linhas): separar prompt building, chamada ao Claude, e persistência de drafts em módulos distintos. Unificar `generate_drafts` e `regenerate_draft` (80% de código duplicado)
- Migrar inline styles de `campaigns.js` para classes CSS com design tokens. Extrair `statusColors`/`statusLabels` duplicados para constantes compartilhadas
- Corrigir `event.target` global implícito em `generateVariations` para receber event como parâmetro
- Corrigir `--space-xxl: 20px` para 32px e consolidar tokens de cor (6 níveis de cinza para 4)

### Bloco 5: Mobile e Acessibilidade (MÉDIO)

- Mobile: mostrar pelo menos 1-2 linhas do texto do draft nos pills (não só o label)
- Mobile: adicionar acesso ao context-panel via drawer/botão
- Adicionar testes para error paths do draft_engine (quando Claude API falha)
- Adicionar `aria-label` em todos os botões com ícone (hamburger, gear, regen, attach, close)
- Corrigir contraste dos cinzas: `--color-text-light` de #999 para #767676, `--color-text-muted` de #888 para #595959

### Bloco 6: Polish (BAIXO)

- Adicionar índices no banco: `messages(conversation_id)`, `drafts(conversation_id, status)`, `edit_pairs(conversation_id)`, `campaign_contacts(campaign_id, status)`
- Adicionar busca/filtro na sidebar de conversas
- Adicionar tokens de tipografia (`--font-size-sm/md/lg`) e transition (`--transition-fast/normal`) ao design system
- Webhook validation: verificar se Evolution API manda header/token que possa ser validado

## O que NÃO muda

- Não migra para PostgreSQL (SQLite com WAL é suficiente para o volume atual)
- Não introduz structured logging, métricas, ou tracing (logging.INFO para stdout basta)
- Não implementa WebSocket channels (broadcast total funciona com poucos operadores)
- Não introduz repository pattern ou domain entities (SQL direto é pragmático para este porte)
- Não adiciona CI/CD (Dockerfile resolve reprodutibilidade)
- Não implementa undo de envio (WhatsApp não suporta recall confiável via API)

## Impacto

- **Backend:** `database.py`, `send_executor.py`, `messages.py`, `draft_engine.py`, `evolution.py`, `scheduler.py`, `campaign_executor.py`, `main.py`, `config.py`
- **Frontend:** `js/ui/drafts.js`, `js/ui/compose.js`, `js/ui/campaigns.js`, `js/main.js`, `js/ws.js`, `css/tokens.css`, `css/campaigns.css`, `index.html`
- **Testes:** `conftest.py` (eliminação dos 16 patches), novos testes de error paths
- **Infra:** novo `Dockerfile`, `docker-compose.yml`, script de backup
- **Deps:** `pyproject.toml` (Pillow)

## Fonte

Baseado no relatório consolidado da war room (`openspec/war-room-report.md`) com análises de 4 especialistas: Arquitetura, QA, DevOps, e Design.
