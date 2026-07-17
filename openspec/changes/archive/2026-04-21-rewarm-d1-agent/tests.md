## Test Strategy

- **Backend**: pytest com fixtures de `tests/conftest.py` (db em memória, cliente FastAPI, patches do `claude_client`). Convenção: arquivos em `tests/test_*.py`.
- **Frontend E2E**: Playwright em `tests/e2e/` (convenção existente). Usa Evolution mock + seed de conversas via fixture Python.
- **Cobertura alvo**: todo scenario da spec mapeado para ao menos 1 teste. Unit para lógica pura (query SQL em isolado, parser de decisão do agente), integration para rotas FastAPI (com `TestClient`), e2e só para o caminho de UI principal (clicar botão → ver preview → editar → enviar).
- **Mocks padrão**: `claude_client.call_haiku` substituído em testes para retornar JSON pré-definido. `message_sender.send_message` patched para registrar invocação sem chamar Evolution. Para timings do rate-limit, `asyncio.sleep` pode ser patched com `monkeypatch` para acelerar testes.
- **Red-Green-Refactor**: todos os testes abaixo SHALL ser escritos e rodados antes da implementação (devem falhar com erro de import/atributo inexistente); implementação os leva ao verde.

## Spec-to-Test Mapping

### Capability: rewarm-agent

#### Scenario: Conversa elegível é incluída
- **Test type**: unit
- **Test file**: `tests/test_rewarm_query.py`
- **Test name**: `test_query_includes_eligible_conversation`
- **Setup (GIVEN)**: Banco com uma `conversation` (funnel_product='CDO', funnel_stage='handbook_sent'), uma `message` criada ontem, sem drafts pendentes
- **Action (WHEN)**: Chamar `select_rewarm_candidates(db)` do `app/services/rewarm_engine.py`
- **Assert (THEN)**: Resultado contém a conversa

#### Scenario: Conversa com produto diferente é excluída
- **Test type**: unit
- **Test file**: `tests/test_rewarm_query.py`
- **Test name**: `test_query_excludes_other_product`
- **Setup (GIVEN)**: Conversa com `funnel_product='outro-curso'`, stage válido, mensagem ontem
- **Action (WHEN)**: `select_rewarm_candidates(db)`
- **Assert (THEN)**: Resultado vazio

#### Scenario: Conversa em stage diferente é excluída
- **Test type**: unit
- **Test file**: `tests/test_rewarm_query.py`
- **Test name**: `test_query_excludes_other_stage`
- **Setup (GIVEN)**: Conversa CDO mas `funnel_stage='qualifying'`, mensagem ontem
- **Action (WHEN)**: `select_rewarm_candidates(db)`
- **Assert (THEN)**: Resultado vazio
- **Edge cases**: Cobrir também `decided` e `purchased` como stages excluídos em parametrização

#### Scenario: Conversa sem mensagem em D-1 é excluída
- **Test type**: unit
- **Test file**: `tests/test_rewarm_query.py`
- **Test name**: `test_query_excludes_conversation_without_yesterday_message`
- **Setup (GIVEN)**: Conversa CDO/handbook_sent com última mensagem há 3 dias
- **Action (WHEN)**: `select_rewarm_candidates(db)`
- **Assert (THEN)**: Resultado vazio

#### Scenario: Conversa com draft pendente é excluída
- **Test type**: unit
- **Test file**: `tests/test_rewarm_query.py`
- **Test name**: `test_query_excludes_conversation_with_pending_draft`
- **Setup (GIVEN)**: Conversa CDO/handbook_sent, mensagem ontem, e draft com `sent_at IS NULL`
- **Action (WHEN)**: `select_rewarm_candidates(db)`
- **Assert (THEN)**: Resultado vazio

#### Scenario: Conversa já purchased é excluída
- **Test type**: unit
- **Test file**: `tests/test_rewarm_query.py`
- **Test name**: `test_query_excludes_purchased`
- **Setup (GIVEN)**: Conversa CDO com `funnel_stage='purchased'`, mensagem ontem
- **Action (WHEN)**: `select_rewarm_candidates(db)`
- **Assert (THEN)**: Resultado vazio

#### Scenario: Agente decide enviar em conversa padrão
- **Test type**: integration
- **Test file**: `tests/test_rewarm_engine.py`
- **Test name**: `test_decide_rewarm_action_returns_send`
- **Setup (GIVEN)**: Conversa fixture com histórico neutro; `claude_client.call_haiku` mockado retornando JSON `{"action":"send","message":"oi, como foi...","reason":"cliente parou após handbook, bom momento"}`
- **Action (WHEN)**: `await decide_rewarm_action(conversation_id)`
- **Assert (THEN)**: Retorna dict com `action='send'`, `message` não vazio, `reason` não vazio

#### Scenario: Agente pula quando cliente expressou desinteresse
- **Test type**: integration
- **Test file**: `tests/test_rewarm_engine.py`
- **Test name**: `test_decide_rewarm_action_skips_when_customer_declined`
- **Setup (GIVEN)**: `claude_client.call_haiku` mockado retornando `{"action":"skip","reason":"cliente pediu para parar explicitamente"}`
- **Action (WHEN)**: `await decide_rewarm_action(conversation_id)`
- **Assert (THEN)**: `action='skip'`, `reason` menciona pedido de parar, `message` ausente ou vazio

#### Scenario: Agente pula quando cliente já comprou em outro lugar
- **Test type**: integration
- **Test file**: `tests/test_rewarm_engine.py`
- **Test name**: `test_decide_rewarm_action_skips_when_customer_bought_elsewhere`
- **Setup (GIVEN)**: Mock retorna `{"action":"skip","reason":"comprou em outro lugar"}`
- **Action (WHEN)**: `await decide_rewarm_action(conversation_id)`
- **Assert (THEN)**: `action='skip'`, `reason` menciona compra em outro lugar

#### Scenario: Mensagem respeita tom da conversa
- **Test type**: integration (snapshot do prompt)
- **Test file**: `tests/test_rewarm_engine.py`
- **Test name**: `test_rewarm_prompt_includes_conversation_history_and_tone_instruction`
- **Setup (GIVEN)**: Fixture de conversa com tom informal conhecido
- **Action (WHEN)**: Interceptar o prompt passado a `call_haiku` ao chamar `decide_rewarm_action`
- **Assert (THEN)**: Prompt contém as mensagens da conversa (snapshot) E inclui instrução explícita de espelhar o tom da conversa
- **Edge cases**: Verificar que a instrução de "pode retornar skip com razão" está no prompt

#### Scenario: Preview retorna lista ordenada de sugestões
- **Test type**: integration
- **Test file**: `tests/test_rewarm_routes.py`
- **Test name**: `test_preview_returns_all_decisions`
- **Setup (GIVEN)**: Banco com 3 conversas candidatas; `decide_rewarm_action` mockado para retornar send/send/skip
- **Action (WHEN)**: Cliente autenticado chama `POST /rewarm/preview`
- **Assert (THEN)**: HTTP 200; corpo array com 3 itens; cada item tem `item_id`, `conversation_id`, `action`, `reason`; itens send têm `message`

#### Scenario: Preview sem candidatas retorna lista vazia
- **Test type**: integration
- **Test file**: `tests/test_rewarm_routes.py`
- **Test name**: `test_preview_returns_empty_when_no_candidates`
- **Setup (GIVEN)**: Banco sem conversas elegíveis
- **Action (WHEN)**: `POST /rewarm/preview`
- **Assert (THEN)**: HTTP 200; corpo `[]`

#### Scenario: Preview requer autenticação de operador
- **Test type**: integration
- **Test file**: `tests/test_rewarm_routes.py`
- **Test name**: `test_preview_requires_auth`
- **Setup (GIVEN)**: Cliente sem cookie de sessão
- **Action (WHEN)**: `POST /rewarm/preview`
- **Assert (THEN)**: HTTP 401

#### Scenario: Execute enfileira envios e retorna imediatamente
- **Test type**: integration
- **Test file**: `tests/test_rewarm_routes.py`
- **Test name**: `test_execute_returns_202_and_schedules_background`
- **Setup (GIVEN)**: Payload com 3 itens aprovados; `message_sender.send_message` e `asyncio.sleep` patched
- **Action (WHEN)**: `POST /rewarm/execute`
- **Assert (THEN)**: HTTP 202 retornado em < 200ms; `send_message` foi invocado 3 vezes (eventualmente, via `await` do background task)
- **Edge cases**: Verificar que o endpoint não bloqueia esperando todos os envios

#### Scenario: Intervalo entre envios respeita janela configurada
- **Test type**: unit
- **Test file**: `tests/test_rewarm_rate_limit.py`
- **Test name**: `test_rate_limit_stays_in_window`
- **Setup (GIVEN)**: Função auxiliar `next_delay()` do módulo de envio em batch
- **Action (WHEN)**: Chamar 1000 vezes e coletar resultados
- **Assert (THEN)**: Todos os valores `>=40` e `<=100`; média próxima de 70
- **Edge cases**: Semear RNG para reproducibilidade

#### Scenario: Item com mensagem editada envia o texto editado
- **Test type**: integration
- **Test file**: `tests/test_rewarm_routes.py`
- **Test name**: `test_execute_uses_edited_message_when_provided`
- **Setup (GIVEN)**: Payload com `message='texto editado'` diferindo do original; `send_message` patched
- **Action (WHEN)**: `POST /rewarm/execute`; aguardar background task
- **Assert (THEN)**: `send_message` foi chamado com `content='texto editado'`

#### Scenario: Envio falho não interrompe o batch
- **Test type**: integration
- **Test file**: `tests/test_rewarm_routes.py`
- **Test name**: `test_execute_continues_after_send_failure`
- **Setup (GIVEN)**: 3 itens; `send_message` patched para levantar exceção no item 2
- **Action (WHEN)**: `POST /rewarm/execute`; aguardar conclusão do batch
- **Assert (THEN)**: Item 1 e 3 foram enviados; exceção do item 2 foi logada; total de envios = 2

#### Scenario: Mensagem enviada é atribuída ao rewarm
- **Test type**: integration
- **Test file**: `tests/test_rewarm_routes.py`
- **Test name**: `test_execute_marks_messages_as_rewarm_reviewed`
- **Setup (GIVEN)**: 1 item aprovado via tela de revisão (modo manual)
- **Action (WHEN)**: `POST /rewarm/execute`; aguardar conclusão
- **Assert (THEN)**: Registro em `messages` tem `sent_by='rewarm_reviewed'`

#### Scenario: Modo automático ligado envia sem revisão
- **Test type**: integration
- **Test file**: `tests/test_rewarm_auto_send.py`
- **Test name**: `test_auto_send_delivers_all_send_items`
- **Setup (GIVEN)**: `REWARM_AUTO_SEND=true`; 2 conversas candidatas, agente retorna `send` para ambas; `send_message` e `asyncio.sleep` patched
- **Action (WHEN)**: Invocar `run_rewarm_auto()` (helper interno)
- **Assert (THEN)**: 2 chamadas a `send_message`; cada registro tem `sent_by='rewarm_agent'`

#### Scenario: Modo automático respeita decisões de skip
- **Test type**: integration
- **Test file**: `tests/test_rewarm_auto_send.py`
- **Test name**: `test_auto_send_skips_when_agent_returns_skip`
- **Setup (GIVEN)**: `REWARM_AUTO_SEND=true`; 2 candidatas: agente retorna send para uma e skip para outra
- **Action (WHEN)**: `run_rewarm_auto()`
- **Assert (THEN)**: Apenas 1 chamada a `send_message`; skip foi logado com `reason`

#### Scenario: Modo manual ignora a flag e sempre retorna preview
- **Test type**: integration
- **Test file**: `tests/test_rewarm_auto_send.py`
- **Test name**: `test_preview_endpoint_ignores_auto_send_flag`
- **Setup (GIVEN)**: `REWARM_AUTO_SEND=true`; 1 candidata
- **Action (WHEN)**: Operador chama `POST /rewarm/preview`
- **Assert (THEN)**: Resposta contém a sugestão; `send_message` NÃO foi chamado

#### Scenario: Operador edita mensagem antes de enviar
- **Test type**: e2e
- **Test file**: `tests/e2e/test_rewarm.spec.ts`
- **Test name**: `operator edits suggested message and sends`
- **Setup (GIVEN)**: Seed backend com 1 conversa candidata; mock Haiku retorna mensagem conhecida
- **Action (WHEN)**: Usuário loga, clica "Reesquentar D-1", espera tela abrir, edita texto, clica "Enviar todos"
- **Assert (THEN)**: Request para `/rewarm/execute` contém texto editado; UI mostra estado de "enviando" e depois confirmação

#### Scenario: Operador remove item do batch
- **Test type**: e2e
- **Test file**: `tests/e2e/test_rewarm.spec.ts`
- **Test name**: `operator removes item before sending`
- **Setup (GIVEN)**: 3 conversas candidatas seeded
- **Action (WHEN)**: Remove 1 item na tela de revisão, clica "Enviar todos"
- **Assert (THEN)**: `/rewarm/execute` recebe 2 itens; item removido não está no payload

#### Scenario: Itens skipados são exibidos mas não enviáveis
- **Test type**: e2e
- **Test file**: `tests/e2e/test_rewarm.spec.ts`
- **Test name**: `skipped items show reason and are not sendable`
- **Setup (GIVEN)**: 1 conversa send + 1 conversa skip seeded
- **Action (WHEN)**: Abre tela de revisão
- **Assert (THEN)**: Item skip visível com razão; não possui campo de edição nem botão de envio individual

#### Scenario: Clique dispara preview e abre revisão
- **Test type**: e2e
- **Test file**: `tests/e2e/test_rewarm.spec.ts`
- **Test name**: `clicking button triggers preview and opens review`
- **Setup (GIVEN)**: 2 conversas candidatas
- **Action (WHEN)**: Clica em "Reesquentar D-1"
- **Assert (THEN)**: Loading aparece; tela de revisão abre com 2 itens

#### Scenario: Preview vazio mostra mensagem amigável
- **Test type**: e2e
- **Test file**: `tests/e2e/test_rewarm.spec.ts`
- **Test name**: `empty preview shows friendly message`
- **Setup (GIVEN)**: Zero candidatas
- **Action (WHEN)**: Clica em "Reesquentar D-1"
- **Assert (THEN)**: Tela mostra mensagem "sem conversas elegíveis"

## Coverage Summary

| Capability | Scenario | Test file | Test name | Type |
|------------|----------|-----------|-----------|------|
| rewarm-agent | Conversa elegível é incluída | `tests/test_rewarm_query.py` | `test_query_includes_eligible_conversation` | unit |
| rewarm-agent | Conversa com produto diferente é excluída | `tests/test_rewarm_query.py` | `test_query_excludes_other_product` | unit |
| rewarm-agent | Conversa em stage diferente é excluída | `tests/test_rewarm_query.py` | `test_query_excludes_other_stage` | unit |
| rewarm-agent | Conversa sem mensagem em D-1 é excluída | `tests/test_rewarm_query.py` | `test_query_excludes_conversation_without_yesterday_message` | unit |
| rewarm-agent | Conversa com draft pendente é excluída | `tests/test_rewarm_query.py` | `test_query_excludes_conversation_with_pending_draft` | unit |
| rewarm-agent | Conversa já purchased é excluída | `tests/test_rewarm_query.py` | `test_query_excludes_purchased` | unit |
| rewarm-agent | Agente decide enviar em conversa padrão | `tests/test_rewarm_engine.py` | `test_decide_rewarm_action_returns_send` | integration |
| rewarm-agent | Agente pula quando cliente expressou desinteresse | `tests/test_rewarm_engine.py` | `test_decide_rewarm_action_skips_when_customer_declined` | integration |
| rewarm-agent | Agente pula quando cliente já comprou em outro lugar | `tests/test_rewarm_engine.py` | `test_decide_rewarm_action_skips_when_customer_bought_elsewhere` | integration |
| rewarm-agent | Mensagem respeita tom da conversa | `tests/test_rewarm_engine.py` | `test_rewarm_prompt_includes_conversation_history_and_tone_instruction` | integration |
| rewarm-agent | Preview retorna lista ordenada de sugestões | `tests/test_rewarm_routes.py` | `test_preview_returns_all_decisions` | integration |
| rewarm-agent | Preview sem candidatas retorna lista vazia | `tests/test_rewarm_routes.py` | `test_preview_returns_empty_when_no_candidates` | integration |
| rewarm-agent | Preview requer autenticação de operador | `tests/test_rewarm_routes.py` | `test_preview_requires_auth` | integration |
| rewarm-agent | Execute enfileira envios e retorna imediatamente | `tests/test_rewarm_routes.py` | `test_execute_returns_202_and_schedules_background` | integration |
| rewarm-agent | Intervalo entre envios respeita janela configurada | `tests/test_rewarm_rate_limit.py` | `test_rate_limit_stays_in_window` | unit |
| rewarm-agent | Item com mensagem editada envia o texto editado | `tests/test_rewarm_routes.py` | `test_execute_uses_edited_message_when_provided` | integration |
| rewarm-agent | Envio falho não interrompe o batch | `tests/test_rewarm_routes.py` | `test_execute_continues_after_send_failure` | integration |
| rewarm-agent | Mensagem enviada é atribuída ao rewarm | `tests/test_rewarm_routes.py` | `test_execute_marks_messages_as_rewarm_reviewed` | integration |
| rewarm-agent | Modo automático ligado envia sem revisão | `tests/test_rewarm_auto_send.py` | `test_auto_send_delivers_all_send_items` | integration |
| rewarm-agent | Modo automático respeita decisões de skip | `tests/test_rewarm_auto_send.py` | `test_auto_send_skips_when_agent_returns_skip` | integration |
| rewarm-agent | Modo manual ignora a flag e sempre retorna preview | `tests/test_rewarm_auto_send.py` | `test_preview_endpoint_ignores_auto_send_flag` | integration |
| rewarm-agent | Operador edita mensagem antes de enviar | `tests/e2e/test_rewarm.spec.ts` | `operator edits suggested message and sends` | e2e |
| rewarm-agent | Operador remove item do batch | `tests/e2e/test_rewarm.spec.ts` | `operator removes item before sending` | e2e |
| rewarm-agent | Itens skipados são exibidos mas não enviáveis | `tests/e2e/test_rewarm.spec.ts` | `skipped items show reason and are not sendable` | e2e |
| rewarm-agent | Clique dispara preview e abre revisão | `tests/e2e/test_rewarm.spec.ts` | `clicking button triggers preview and opens review` | e2e |
| rewarm-agent | Preview vazio mostra mensagem amigável | `tests/e2e/test_rewarm.spec.ts` | `empty preview shows friendly message` | e2e |
