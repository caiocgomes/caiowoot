## Why

Operadores que aceitam drafts da IA sem personalizar não convertem vendas. Sem visibilidade sobre o comportamento de cada operador por conversa, o gestor (Caio) não consegue identificar padrões problemáticos, dar feedback com exemplos concretos, nem detectar vendas que podem ser salvas com intervenção direta. Hoje o sistema coleta todos os dados necessários (edit_pairs, strategic_annotations, messages com sent_by) mas não agrega nem analisa.

## What Changes

- Novo serviço de análise que processa conversas de um período, avalia qualidade por operador e identifica vendas recuperáveis
- Análise por conversa via LLM: verifica erros factuais contra knowledge base, avalia nível de personalização do operador, classifica status da venda
- Síntese por operador via LLM: identifica padrões de comportamento (ex: piloto automático), gera exemplos concretos de onde personalizar teria feito diferença
- Lista de vendas salvável com sugestão de abordagem para retomar
- Página admin-only `/admin/coaching` para visualizar resultados
- Endpoint para trigger manual da análise + possibilidade de agendamento via cron
- Novas tabelas SQLite para persistir análises e runs

## Capabilities

### New Capabilities

- `conversation-analysis`: Análise individual de conversas via LLM — erros factuais, nível de personalização, status da venda, potencial de recuperação
- `operator-coaching`: Síntese por operador com padrões de comportamento, exemplos concretos de melhoria, métricas de uso do copiloto (taxa de edição, regeneração). Inclui lista de vendas salvável. Página admin-only.

### Modified Capabilities

_Nenhuma. Funcionalidade nova que consome dados existentes sem alterar comportamento atual._

## Impact

- `app/services/` — novos módulos de análise (conversation_analysis.py, operator_coaching.py)
- `app/routes/` — nova rota admin para coaching
- `app/database.py` — novas migrations (conversation_assessments, operator_digests, analysis_runs)
- `app/static/` — nova página coaching.html
- `app/auth.py` — reutiliza is_admin() existente
- Dependência de chamadas LLM (Haiku para análise individual, Sonnet para síntese)
- Sem mudança em APIs existentes, sem breaking changes
