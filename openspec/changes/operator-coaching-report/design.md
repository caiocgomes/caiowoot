## Context

O CaioWoot já coleta todos os dados necessários para avaliar desempenho de operadores: `messages.sent_by` identifica quem mandou, `edit_pairs` registra se o operador editou o draft ou aceitou no piloto automático, `strategic_annotation` analisa a decisão por mensagem, e `knowledge/*.md` contém a base factual. O que falta é agregar esses dados numa análise por conversa e por operador, com exemplos concretos e lista de vendas recuperáveis.

O sistema tem uma semana de dados, dois operadores ativos (Caio e Miguel), e o relatório é exclusivo para o admin (Caio).

## Goals / Non-Goals

**Goals:**
- Detectar padrão de "piloto automático" (operador aceita drafts sem personalizar)
- Identificar erros factuais cruzando respostas com knowledge base
- Gerar lista acionável de vendas que podem ser salvas com intervenção
- Coaching com exemplos concretos das conversas do operador, não métricas abstratas
- Relatório com tom direto e sem eufemismo (só o admin vê)

**Non-Goals:**
- Comparação entre operadores (ranking/leaderboard)
- Feedback visível para operadores
- Real-time alerts (daily é suficiente por agora)
- Análise de conversas sem nenhuma mensagem outbound (apenas flaggar como "sem resposta")
- Dashboard de métricas com gráficos (texto com números basta)

## Decisions

### 1. Dois módulos de serviço separados: conversation_analysis.py e operator_coaching.py

O `conversation_analysis.py` processa uma conversa individual e retorna o assessment. O `operator_coaching.py` orquestra o run: busca conversas do período, chama conversation_analysis para cada uma com concurrency limitada, depois gera o digest por operador.

Separar em dois permite testar a análise de conversa isoladamente e reusar se no futuro quisermos análise em tempo real.

Alternativa considerada: um módulo monolítico. Descartado porque mistura responsabilidades e dificulta teste.

### 2. Haiku para análise de conversa, Sonnet para digest do operador

A análise individual de conversa é um julgamento focal (uma conversa, um operador). Haiku basta e é barato. O digest do operador precisa sintetizar padrões across múltiplas conversas e gerar exemplos com base numa visão agregada. Sonnet é mais adequado para essa meta-análise.

Alternativa considerada: Haiku para tudo. Descartado porque o digest requer raciocínio de síntese que Haiku não faz bem, especialmente para identificar padrões sutis.

Alternativa considerada: Sonnet para tudo. Descartado por custo desnecessário nas análises individuais.

### 3. Knowledge base incluída no prompt de análise de conversa

Para detectar erros factuais, o LLM precisa da knowledge base. Como o sistema já tem `app/services/knowledge.py` com load e cache por mtime, reutilizamos diretamente. A knowledge base é incluída no system prompt da análise de conversa com cache_control ephemeral (mesmo padrão do draft_engine).

### 4. Três novas tabelas via migrations existentes

Seguindo o padrão existente em `database.py`, adicionamos migrations ao `MIGRATIONS` list:

```sql
-- analysis_runs: tracking de execuções
CREATE TABLE IF NOT EXISTS analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    status TEXT DEFAULT 'running',
    total_conversations INTEGER DEFAULT 0,
    total_operators INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- conversation_assessments: análise por conversa
CREATE TABLE IF NOT EXISTS conversation_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_run_id INTEGER NOT NULL REFERENCES analysis_runs(id),
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    operator_name TEXT,
    engagement_level TEXT,
    sale_status TEXT,
    recovery_potential TEXT,
    recovery_suggestion TEXT,
    factual_issues_json TEXT,
    overall_assessment TEXT,
    metrics_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- operator_digests: síntese por operador
CREATE TABLE IF NOT EXISTS operator_digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_run_id INTEGER NOT NULL REFERENCES analysis_runs(id),
    operator_name TEXT NOT NULL,
    summary TEXT,
    patterns_json TEXT,
    factual_issues_json TEXT,
    salvageable_sales_json TEXT,
    metrics_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5. Rota admin sob /admin/ com checagem is_admin()

Nova rota em `app/routes/admin.py`. Padrão:
```python
operator = get_operator_from_request(request)
if not is_admin(operator):
    return RedirectResponse("/") # ou 403 para API
```

Endpoints:
- `GET /admin/coaching` — serve coaching.html
- `POST /admin/analysis/run` — trigger análise (retorna run_id)
- `GET /admin/analysis/results` — retorna JSON com resultados
- `GET /admin/analysis/status/{run_id}` — progresso do run

### 6. Frontend vanilla como o resto do sistema

Nova página `app/static/coaching.html` seguindo o padrão existente (vanilla HTML/JS, sem framework). Busca dados via fetch do endpoint de results. Estrutura:
1. Header com período e botão "Rodar análise"
2. Seção "Vendas para salvar" (aggregated, priority-ordered)
3. Seções por operador com métricas, padrões e exemplos

### 7. Background processing via asyncio.create_task

Mesmo padrão usado por `generate_annotation` e `generate_drafts`. O endpoint POST retorna imediatamente com o run_id. O processamento roda em background. Frontend pode poll GET /admin/analysis/status/{run_id} para acompanhar progresso.

### 8. Concurrency: asyncio.Semaphore(5) para chamadas LLM

Limita a 5 chamadas simultâneas ao Anthropic API durante o processamento batch. Previne rate limiting e mantém custo previsível.

## Risks / Trade-offs

**[Custo de API na primeira rodada]** → Com uma semana de dados e dezenas de conversas, o custo é baixo (estimativa: < $1 para Haiku + Sonnet). Se o sistema escalar para meses de histórico, rodadas históricas podem custar mais. Mitigação: limitar período máximo a 30 dias por run.

**[Qualidade do julgamento do Haiku]** → Haiku pode não pegar nuances sutis de engagement. Mitigação: incluir métricas quantitativas no prompt (taxa de edição, tempo de resposta) para dar contexto objetivo ao LLM. Se a qualidade não satisfizer, trocar para Sonnet na análise individual.

**[Conversas multi-operador]** → Uma conversa pode ter mensagens de Caio e Miguel. O assessment é por par (conversa, operador), o que pode fragmentar o contexto. Mitigação: o LLM recebe a conversa INTEIRA mas avalia apenas as mensagens do operador em questão.

**[Knowledge base grande no prompt]** → Se a knowledge base crescer muito, pode exceder limites de contexto. Mitigação: mesmo sistema de cache_control ephemeral do draft_engine. No futuro, filtrar knowledge relevante por produto da conversa.

**[Falso positivo em erros factuais]** → Operador pode ter informação correta que não está na knowledge base. O sistema não flagga como erro nesse caso (spec: "não está na base ≠ erro"). Prompt instruído a só flaggar contradições diretas.
