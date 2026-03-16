# War Room Report: CaioWoot

**Data:** 2026-03-15
**Especialistas:** Arquiteto, QA, DevOps, Designer
**Contexto:** Ferramenta interna de copiloto de vendas WhatsApp. Poucos operadores. Caio como operador principal.

---

## Seção 1: Consenso (problemas identificados por 2+ especialistas)

### 1.1 Gestão de conexões com o banco (`get_db()`)

**Apontado por:** Arquiteto, QA, DevOps

O problema mais citado da war room. `get_db()` abre uma conexão nova a cada chamada, sem pool, sem reutilização. Cada request pode abrir 3-4 conexões simultâneas. PRAGMAs (`journal_mode=WAL`, `foreign_keys=ON`) são executados em toda conexão desnecessariamente.

O Arquiteto identifica que o `scheduler.py` abre até 3 conexões (`db`, `db2`, `db3`) numa única iteração. O QA mostra que isso força 16 patches manuais de `get_db` no conftest, que é uma bomba-relógio: qualquer módulo novo que importe `get_db` precisa ser adicionado manualmente à lista, e esquecer causa bugs silenciosos. O DevOps confirma as 50+ chamadas espalhadas pelo codebase, cada uma com `try/finally: await db.close()` manual.

**Recomendação consolidada:** Refatorar `get_db()` para usar dependency injection do FastAPI (`Depends()`). Uma única conexão por request, injetada automaticamente, fechada pelo framework. Elimina os 16 patches do conftest e reduz risco de leak. Alternativamente, um async context manager que garanta cleanup.

### 1.2 Duplicação do fluxo de envio de mensagem

**Apontado por:** Arquiteto, QA

A lógica de envio com edit_pair, marcação de drafts, e trigger de annotation está implementada duas vezes: em `send_executor.py` (texto puro) e em `app/routes/messages.py` (envio com arquivo). São ~80 linhas quase idênticas. O QA confirma que qualquer bug precisa ser corrigido em dois lugares.

**Recomendação consolidada:** Extrair a lógica compartilhada para um único service method que aceite tanto texto quanto arquivo. O handler de `messages.py` com file upload deveria chamar o mesmo executor, passando o arquivo como parâmetro adicional.

### 1.3 `except: pass` nas migrations

**Apontado por:** Arquiteto, QA

`database.py` linha ~330 engole QUALQUER exceção na migration runner, incluindo erros de syntax SQL, disk full, corrupção. Se uma migration falhar por motivo real, o sistema segue operando com schema incompleto e ninguém descobre.

**Recomendação consolidada:** Substituir `except Exception: pass` por tratamento específico para `OperationalError` de "column/table already exists" (que é o caso legítimo). Qualquer outro erro deve ser logado com severidade ERROR e re-raised.

### 1.4 Client HTTP/Anthropic criado a cada chamada

**Apontado por:** Arquiteto, DevOps

`_call_haiku()` instancia `anthropic.AsyncAnthropic()` a cada chamada (3x por draft generation). `evolution.py` cria `httpx.AsyncClient` a cada envio. Desperdiça connection pool HTTP.

**Recomendação consolidada:** Criar singletons para ambos os clients. O Anthropic client pode ser um módulo-level singleton. O httpx client para Evolution API idem. Ambos suportam reutilização de connections.

### 1.5 Inconsistência SCHEMA vs MIGRATIONS

**Apontado por:** Arquiteto, QA

O `SCHEMA` string define tabelas que também existem nas migrations, e as migrations usam `CREATE TABLE IF NOT EXISTS`. Mas o QA encontrou que tabelas de `analysis_runs`, `conversation_assessments` e `operator_digests` existem nas MIGRATIONS mas não no SCHEMA. O conftest aplica `SCHEMA` diretamente, então testes de operator coaching criam tabelas manualmente para compensar.

**Recomendação consolidada:** O SCHEMA deve ser a fonte de verdade do estado atual do banco. Migrations devem ser incrementais sobre versões anteriores. Atualizar o SCHEMA para incluir todas as tabelas que existem em produção, e garantir que o conftest aplique tanto SCHEMA quanto MIGRATIONS.

### 1.6 Fire-and-forget sem controle (`asyncio.create_task`)

**Apontado por:** Arquiteto, DevOps

Background tasks (draft generation, strategic annotation, analysis) são disparadas com `asyncio.create_task()` sem rastreamento. Se falharem, a exceção é logada mas o operador não é notificado. Se o servidor parar, o trabalho é perdido. O DevOps nota que não há como saber se as background loops (scheduler, campaign_executor) ainda estão vivas.

**Recomendação consolidada:** Para as background loops, adicionar um health check que verifique se estão ativas. Para os tasks de draft/annotation, o erro já é logado, mas o operador deveria receber um broadcast WebSocket de erro quando drafts falham (hoje simplesmente não aparecem). Retry automático não vale o custo para ferramenta interna.

### 1.7 WebSocket broadcast sem canais

**Apontado por:** Arquiteto, Designer

O WebSocketManager envia TODAS as mensagens para TODOS os clientes conectados. Filtragem é feita no frontend. O Arquiteto nota que isso revela dados entre operadores e desperdiça banda. O Designer nota que não existe indicador de status de conexão, então se o WS desconectar o operador não sabe.

**Recomendação consolidada:** Para poucos operadores, o broadcast total é aceitável no curto prazo. A prioridade imediata é adicionar um indicador de status de conexão no frontend (dot verde/vermelho). Channels podem esperar até haver múltiplos operadores com dados sensíveis separados.

### 1.8 Ausência de feedback visual na geração de drafts

**Apontado por:** QA, Designer

O QA identifica que o teste `test_message_triggers_draft_generation` usa `asyncio.sleep(0.5)` e um `if drafts:` que faz o teste nunca falhar. O Designer identifica o mesmo problema pelo lado do usuário: entre a mensagem chegar e os drafts aparecerem (3-5s), não existe nenhum loading indicator. O operador não sabe se o sistema travou ou se está processando.

**Recomendação consolidada:** Adicionar skeleton/spinner no container de drafts quando uma mensagem inbound chega. No lado dos testes, remover o `if drafts:` condicional e usar um mecanismo de polling determinístico em vez de sleep fixo.

---

## Seção 2: Conflitos e Arbitragem

### 2.1 Connection management: pool vs dependency injection vs context manager

- **Arquiteto:** Introduzir connection pool ou conexão compartilhada por request via dependency injection do FastAPI.
- **QA:** Refatorar para injection, eliminando os 16 patches do conftest.
- **DevOps:** Extrair para context manager com cleanup automático, ou usar dependency injection.

**Decisão:** Dependency injection via `Depends()` do FastAPI. É a solução que resolve tanto o problema de produção (conexões multiplicadas) quanto o de testes (16 patches). Context manager sozinho não elimina os patches. Pool é over-engineering para SQLite.

### 2.2 Prioridade do Dockerfile vs problemas de código

- **DevOps:** Dockerfile + docker-compose é CRÍTICO e deve ser feito primeiro.
- **Arquiteto:** Gestão de conexões é o problema mais grave.
- **QA:** Corrigir migrations é prioridade 1.

**Decisão:** O Dockerfile é infraestrutura operacional e leva ~1 hora. Deve ser feito primeiro justamente porque é rápido e resolve restart automático. Mas o problema de conexões é mais grave em termos de correção de arquitetura e deve vir logo em seguida. Migrations em terceiro.

### 2.3 Webhook validation: segurança vs pragmatismo

- **DevOps:** Webhook sem autenticação é um risco. Qualquer pessoa pode injetar mensagens falsas.
- **Arquiteto:** Não mencionou como problema prioritário.

**Decisão:** Para ferramenta interna, o risco é baixo se o endpoint não está exposto publicamente. Verificar se a Evolution API manda algum header/token que possa ser validado é uma melhoria de baixo esforço que vale fazer. Não é crítico.

### 2.4 `datetime.utcnow()` deprecation

- **QA:** `datetime.utcnow()` é deprecated desde Python 3.12 e pode causar bug na dedup window.
- **Arquiteto:** Mencionou como inconsistência com `now_local()` usado no resto do código.

**Decisão:** Corrigir para `datetime.now(timezone.utc)` em todos os pontos. Baixo esforço, evita bugs sutis de timezone. Incluir na próxima refatoração.

---

## Seção 3: Findings Únicos de Alto Impacto

### 3.1 Pillow não declarada como dependência (DevOps)

`from PIL import Image` é importada em `campaign_executor.py` mas PIL/Pillow não está no `pyproject.toml`. Funciona hoje por ser dependência transitiva, mas vai quebrar em qualquer instalação limpa. Qualquer campanha com imagem falharia.

**Impacto:** Alto. Correção trivial: `uv add Pillow`.

### 3.2 Auto-select do primeiro draft cria viés (Designer)

O primeiro draft ("Direta") é auto-selecionado e já preenche o textarea. O operador não vê os 3 lado a lado antes de decidir. Isso cria viés sistemático para a primeira variação, comprometendo o learning loop inteiro, já que os edit_pairs vão refletir a preferência posicional e não a preferência real.

**Impacto:** Alto. O learning loop é o diferencial do produto. Se os dados de treinamento estão enviesados pela posição, o sistema aprende a coisa errada. Solução: não auto-selecionar, mostrar os 3 cards sem pré-selecionar nenhum.

### 3.3 `--space-xxl` menor que `--space-xl` (Designer)

`--space-xxl: 20px` é menor que `--space-xl: 24px`. Inversão semântica que afeta todo componente que usa xxl. Correção trivial mas impacto visual real.

### 3.4 12+ chamadas de `alert()` nativo no frontend (Designer)

Erros e confirmações usam `alert()` e `confirm()` nativos do browser. Bloqueia a thread, é disruptivo, e não segue padrão visual. Para uma ferramenta de produtividade onde o operador está em fluxo contínuo de vendas, cada `alert()` é uma interrupção forçada.

**Impacto:** Médio-alto. Toast/snackbar system é um investimento que melhora toda a UX de uma vez.

### 3.5 Mobile: draft pills sem texto (Designer)

No mobile, os draft cards viram pills que mostram só o label (Direta/Consultiva/Casual) sem o texto. O operador precisa clicar em cada pill para ver o texto. Na prática, está escolhendo cegamente.

**Impacto:** Alto se mobile é usado em campo. Médio se desktop é o uso primário.

### 3.6 Cores hardcoded no JS de campanhas (Designer)

`campaigns.js` usa inline styles com cores hardcoded (`#888`, `#25D366`, etc.) em vez de design tokens. Isso desconecta completamente as campanhas do design system. Qualquer mudança visual futura vai ignorar as campanhas.

### 3.7 Testes de campanhas com imagem inexistentes (QA)

`_recompress_image` depende de PIL e nunca é testada. Combinado com o finding do DevOps de que PIL nem é dependência declarada, campanhas com imagem são uma funcionalidade não testada e potencialmente quebrada.

### 3.8 `event.target` global implícito em campaigns.js (Designer)

`generateVariations` usa `event.target` como variável global implícita. Funciona em Chrome mas não é padronizado. Pode quebrar silenciosamente em outros browsers.

---

## Seção 4: Plano de Ação Priorizado

### CRÍTICO

| # | Ação | Risco mitigado | Endossado por | Complexidade |
|---|------|---------------|---------------|-------------|
| 1 | Adicionar Pillow ao `pyproject.toml` | Campanhas com imagem quebram em instalação limpa | DevOps | Pequeno |
| 2 | Corrigir `except: pass` nas migrations para tratar apenas `OperationalError` esperado | Perda silenciosa de migrations, schema incompleto | Arquiteto, QA | Pequeno |
| 3 | Criar Dockerfile + docker-compose com volume para `data/` e restart policy | Serviço morre e não volta após reboot | DevOps | Pequeno |
| 4 | Refatorar `get_db()` para dependency injection via FastAPI `Depends()` | Conexões multiplicadas, 16 patches no conftest, risco de leak | Arquiteto, QA, DevOps | Grande |

### ALTO

| # | Ação | Risco mitigado | Endossado por | Complexidade |
|---|------|---------------|---------------|-------------|
| 5 | Unificar lógica de envio de `messages.py` e `send_executor.py` em um único service | Duplicação de ~80 linhas, bugs que precisam fix em 2 lugares | Arquiteto, QA | Médio |
| 6 | Adicionar loading state (skeleton/spinner) para geração de drafts | Operador não sabe se sistema está processando | QA, Designer | Pequeno |
| 7 | Não auto-selecionar primeiro draft, mostrar os 3 sem pré-seleção | Viés posicional contamina learning loop | Designer | Pequeno |
| 8 | Sincronizar SCHEMA com MIGRATIONS (incluir tabelas de analysis) | Testes com schema incompleto, bugs silenciosos | Arquiteto, QA | Pequeno |
| 9 | Singleton para Anthropic client e httpx client | Desperdício de connection pool, overhead desnecessário | Arquiteto, DevOps | Pequeno |
| 10 | Adicionar indicador de status de conexão WebSocket no frontend | Operador não sabe quando parou de receber updates | Designer | Pequeno |
| 11 | Substituir `alert()`/`confirm()` por toast/snackbar system | Interrupções forçadas no fluxo do operador | Designer | Médio |
| 12 | Adicionar backup automatizado do SQLite (cron + `.backup`) | Perda total de dados se disco falhar | DevOps | Pequeno |

### MÉDIO

| # | Ação | Risco mitigado | Endossado por | Complexidade |
|---|------|---------------|---------------|-------------|
| 13 | Decompor `draft_engine.py` (separar prompt building, Claude call, persistência) | God module com 650 linhas, duplicação generate/regenerate | Arquiteto | Grande |
| 14 | Adicionar health check endpoint (`GET /health`) | Sem visibilidade sobre saúde do sistema e background tasks | DevOps | Pequeno |
| 15 | Migrar inline styles de `campaigns.js` para CSS com tokens | Campanhas desconectadas do design system | Designer | Médio |
| 16 | Corrigir `--space-xxl` e consolidar tokens de cor (6 cinzas para 4) | Inconsistência semântica no design system | Designer | Pequeno |
| 17 | Adicionar `datetime.now(timezone.utc)` em vez de `datetime.utcnow()` | Bug sutil de timezone na dedup window | QA, Arquiteto | Pequeno |
| 18 | Mobile: mostrar texto nos draft pills e acesso ao context-panel | Operador mobile escolhe drafts cegamente | Designer | Médio |
| 19 | Corrigir `event.target` global em `campaigns.js` | Quebra silenciosa em browsers não-Chrome | Designer | Pequeno |
| 20 | Adicionar testes para error paths do draft_engine (falha do Claude) | Operador fica sem feedback quando API falha | QA | Pequeno |

### BAIXO

| # | Ação | Risco mitigado | Endossado por | Complexidade |
|---|------|---------------|---------------|-------------|
| 21 | Adicionar índices no banco para queries frequentes | Performance degrada com volume | Arquiteto | Pequeno |
| 22 | Adicionar busca/filtro na sidebar de conversas | Operador com 100+ conversas precisa scrollar | Designer | Médio |
| 23 | Adicionar aria-labels em botões com ícone | Inacessível para screen readers | Designer | Pequeno |
| 24 | Corrigir contraste dos cinzas (mínimo WCAG 4.5:1) | Acessibilidade visual | Designer | Pequeno |
| 25 | Webhook validation (verificar header/token da Evolution API) | Injeção de mensagens falsas | DevOps | Pequeno |
| 26 | Adicionar tokens de tipografia e transition ao design system | Inconsistência visual em mudanças futuras | Designer | Pequeno |

---

## Seção 5: O que NÃO fazer

### 5.1 Migrar para PostgreSQL ou outro RDBMS
O Arquiteto nota que SQLite é single-writer e vai criar contention com carga. Verdade, mas CaioWoot tem poucos operadores e volume baixo. SQLite com WAL é mais que suficiente. A complexidade operacional de PostgreSQL não se justifica.

### 5.2 Implementar structured logging, métricas, tracing
O DevOps descartou corretamente, mas vale reforçar: Datadog/Grafana/OpenTelemetry é over-engineering para ferramenta interna. `logging.INFO` para stdout é suficiente. O health check endpoint cobre a necessidade de monitoramento.

### 5.3 WebSocket com canais/rooms
O Arquiteto recomenda channels para separar dados entre operadores. Com poucos operadores (potencialmente só Caio), o broadcast total funciona. A filtragem no frontend é suficiente. Channels adicionam complexidade de state management no servidor.

### 5.4 Repository pattern / Domain entities
O Arquiteto identifica que não há camada de repositório nem abstrações de domínio. Para uma ferramenta deste porte, SQL direto nos handlers e services é pragmático e legível. Introduzir repository pattern adicionaria indireção sem benefício proporcional. A exceção é `get_db()` que precisa de injection, mas isso é diferente de um full DAL.

### 5.5 Testes end-to-end com VCR/cassettes
O QA sugere testes sem mocks do Claude usando respostas pré-gravadas. O custo de manter cassettes atualizadas com mudanças de prompt é alto e o benefício marginal sobre os mocks atuais é pequeno. Os mocks cobrem o parsing de tool_use/text blocks adequadamente.

### 5.6 CI/CD sofisticado
O DevOps não recomendou, mas vale explicitar: GitHub Actions com lint/test/deploy automático seria bom, porém o custo de setup e manutenção para uma ferramenta interna com deploy manual infrequente não compensa agora. O Dockerfile já resolve a reprodutibilidade.

### 5.7 Undo de envio de mensagem
O Designer sugere como nice-to-have. WhatsApp não suporta recall de mensagens de forma confiável via API. A complexidade de implementar um "undo" com timer (tipo Gmail) para interceptar o envio não vale o esforço para o volume atual.

### 5.8 Dashboard no estado vazio (main-empty)
O Designer sugere mostrar métricas quando nenhuma conversa está selecionada. Custo de implementação médio, benefício marginal. O operador raramente está nessa tela, já que seleciona uma conversa imediatamente.

---

## Nota Final

Os 4 relatórios convergem em um diagnóstico claro: CaioWoot é um protótipo que evoluiu organicamente e funciona bem para o cenário atual. Os problemas não são conceituais (o learning loop, o fluxo de 3 drafts, o pipeline de annotation/retrieval são bem pensados). Os problemas são de engenharia incremental: duplicação de código, gestão de conexões improvisada, frontend sem feedback adequado.

A priorização acima reflete o contexto real: ferramenta interna, poucos operadores, Caio como operador principal. Os itens CRÍTICOS e ALTO são acionáveis e concretos. Os itens na seção "O que NÃO fazer" economizam tempo que seria gasto em over-engineering sem retorno.
