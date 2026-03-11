## ADDED Requirements

### Requirement: Testes do endpoint classify_conversation
O sistema de testes SHALL cobrir o endpoint POST /conversations/{id}/classify incluindo happy path com atualização de funnel, conversa sem mensagens, e conversa inexistente.

#### Scenario: Classificar conversa com sucesso e atualizar funnel
- **WHEN** POST `/conversations/{id}/classify` com conversa que tem mensagens
- **AND** generate_situation_summary retorna product e stage
- **THEN** retorna 200 com summary, product e stage
- **AND** conversation no banco tem funnel_product e funnel_stage atualizados

#### Scenario: Classificar conversa sem mensagens
- **WHEN** POST `/conversations/{id}/classify` com conversa sem mensagens
- **THEN** retorna 200 com summary, product e stage todos null

#### Scenario: Classificar conversa inexistente
- **WHEN** POST `/conversations/99999/classify`
- **THEN** retorna 404

### Requirement: Testes dos endpoints admin de analysis
O sistema de testes SHALL cobrir os endpoints de status e results de analysis runs.

#### Scenario: Consultar status de analysis run existente
- **WHEN** GET `/admin/analysis/status/{id}` com run existente
- **THEN** retorna 200 com run_id, status, period, totals e assessments_completed

#### Scenario: Consultar status de run inexistente
- **WHEN** GET `/admin/analysis/status/99999`
- **THEN** retorna 404

#### Scenario: Consultar results com dados completos
- **WHEN** GET `/admin/analysis/results?run_id={id}` com run que tem assessments e digests
- **THEN** retorna 200 com run, operator_digests, salvageable_sales, unanswered e assessments_by_operator

#### Scenario: Consultar results sem runs
- **WHEN** GET `/admin/analysis/results` sem nenhuma run no banco
- **THEN** retorna 200 com run null e listas vazias

#### Scenario: Endpoints admin rejeitam não-admin
- **WHEN** qualquer endpoint admin é chamado sem sessão de admin
- **THEN** retorna 403

### Requirement: Testes de JSON parse fallback no operator digest
O sistema de testes SHALL cobrir o parsing de respostas malformadas da LLM na geração de operator digest.

#### Scenario: Resposta LLM com JSON válido
- **WHEN** _generate_operator_digest recebe resposta JSON válida da LLM
- **THEN** retorna o dict parseado corretamente

#### Scenario: Resposta LLM com JSON embutido em texto
- **WHEN** _generate_operator_digest recebe resposta com texto + JSON embutido
- **THEN** extrai o JSON do texto e retorna o dict

#### Scenario: Resposta LLM completamente inválida
- **WHEN** _generate_operator_digest recebe texto sem JSON
- **THEN** retorna dict com summary=texto e listas vazias
