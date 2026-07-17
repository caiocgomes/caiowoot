## MODIFIED Requirements

### Requirement: Query de conversas candidatas a reesquentamento D-1
O sistema SHALL selecionar como candidatas a reesquentamento exatamente as conversas que, no momento do clique, satisfazem todos os critérios: `funnel_product = 'curso-cdo'`, `funnel_stage IN ('handbook_sent', 'link_sent')`, e a **última** mensagem da conversa foi em uma data de referência configurável (default: ontem local). O sistema SHALL aceitar uma `reference_date` arbitrária em formato ISO `YYYY-MM-DD` para o filtro temporal, substituindo o hardcoded `DATE('now','-1 day')`. Conversas cuja última mensagem não bate com a `reference_date` SHALL NOT aparecer.

#### Scenario: Query usa ontem como default quando reference_date não é fornecido
- **GIVEN** `select_rewarm_candidates(db)` é chamado sem `reference_date`
- **WHEN** a query executa
- **THEN** a data de referência usada SHALL ser ontem no fuso local (`now_local() - 1 day`)

#### Scenario: Query usa reference_date quando fornecida
- **GIVEN** `select_rewarm_candidates(db, reference_date="2026-04-17")` é chamado em 2026-04-20
- **WHEN** a query executa
- **THEN** apenas conversas cuja `DATE(MAX(messages.created_at)) = '2026-04-17'` SHALL ser retornadas

#### Scenario: Conversa elegível em referência sexta recuperada na segunda
- **GIVEN** conversa tem última mensagem em sexta 2026-04-17 e hoje é segunda 2026-04-20
- **AND** operator chama com `reference_date="2026-04-17"`
- **THEN** a conversa SHALL aparecer na lista (o filtro antigo "ontem" não retornaria, pois ontem é domingo)

## ADDED Requirements

### Requirement: Endpoint GET /rewarm/suggested-date
O sistema SHALL expor `GET /rewarm/suggested-date` retornando a data sugerida para o seletor de data na UI, com base no dia da semana atual no fuso local do servidor. O contrato da resposta SHALL ser `{"date": "YYYY-MM-DD", "label": "<nome-do-dia-em-portugues>"}`.

#### Scenario: Segunda-feira sugere sexta-feira passada
- **GIVEN** hoje é segunda-feira
- **WHEN** o cliente faz `GET /rewarm/suggested-date`
- **THEN** a resposta SHALL conter `date` igual a 3 dias atrás (sexta passada) e `label` igual a "sexta-feira"

#### Scenario: Outros dias da semana sugerem ontem
- **GIVEN** hoje é qualquer dia exceto segunda-feira
- **WHEN** o cliente faz `GET /rewarm/suggested-date`
- **THEN** a resposta SHALL conter `date` igual a ontem e `label` igual ao nome do dia de ontem em português

#### Scenario: Sem tratamento de feriado
- **GIVEN** hoje é dia útil pós-feriado
- **WHEN** o cliente faz `GET /rewarm/suggested-date`
- **THEN** a resposta SHALL seguir a regra por dia da semana sem ajuste por feriado (operador ajusta manualmente no seletor se quiser)

### Requirement: Endpoint POST /rewarm/preview aceita reference_date opcional
O endpoint `POST /rewarm/preview` SHALL aceitar corpo JSON opcional com campo `reference_date` em formato ISO `YYYY-MM-DD`. Sem corpo (ou com `reference_date=null`), o comportamento SHALL ser idêntico ao anterior (usar ontem local). O corpo com data malformada SHALL retornar HTTP 422. A resposta SHALL ser `{"reference_date": "YYYY-MM-DD", "items": [...]}` contendo a data efetivamente usada.

#### Scenario: Preview sem body usa ontem
- **GIVEN** não há conversas elegíveis para datas que não ontem
- **WHEN** operador chama `POST /rewarm/preview` sem body
- **THEN** a resposta SHALL ser 200 com items baseados em ontem e `reference_date` = ontem ISO

#### Scenario: Preview com reference_date válida filtra por essa data
- **GIVEN** existem conversas elegíveis para 2026-04-17
- **WHEN** operador chama `POST /rewarm/preview` com body `{"reference_date": "2026-04-17"}`
- **THEN** a resposta SHALL conter `reference_date="2026-04-17"` e items filtrados por essa data

#### Scenario: Preview com reference_date malformada rejeita
- **GIVEN** body contém `{"reference_date": "nope"}`
- **WHEN** operador chama `POST /rewarm/preview`
- **THEN** a resposta SHALL ser HTTP 422

### Requirement: UI de seletor de data para reesquentamento
A UI SHALL apresentar um botão rotulado "Reesquentar leads" na sidebar. Ao clicar, um modal intermediário SHALL ser exibido com opções de radio: "Ontem", a data sugerida pelo endpoint (se diferente de ontem), e um input livre do tipo date. Confirmação SHALL disparar o preview com a data escolhida e abrir o modal de revisão existente mostrando a data de referência usada.

#### Scenario: Botão abre modal de data antes do preview
- **WHEN** operador clica em "Reesquentar leads"
- **THEN** o modal de seleção de data SHALL aparecer com default no radio apropriado (sugerida se diferente de ontem, senão ontem)

#### Scenario: Modal de revisão mostra data de referência
- **GIVEN** operador escolheu data X e confirmou no modal de data
- **WHEN** o modal de revisão abre
- **THEN** um badge no header SHALL exibir a data X formatada (dd/mm + dia da semana)

#### Scenario: Data livre é aceita sem validação de range
- **WHEN** operador escolhe uma data distante (ex: 30 dias atrás) no input custom e confirma
- **THEN** o preview SHALL ser chamado com essa data e resultado renderizado (lista pode ser vazia, mas sem bloqueio artificial)
