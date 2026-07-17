# rewarm-agent Specification

## Purpose
TBD - created by archiving change rewarm-d1-agent. Update Purpose after archive.
## Requirements
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

### Requirement: Agente decide send ou skip por conversa
O sistema SHALL, para cada conversa candidata, invocar uma função `decide_rewarm_action(conversation_id)` que lê o histórico completo da conversa, chama Claude Haiku com o prompt dedicado de reesquentamento, e retorna um resultado estruturado no formato `{action: 'send'|'skip', message?: str, reason: str}`. Quando `action='send'`, `message` SHALL conter uma mensagem em português brasileiro no tom espelhado da conversa. Quando `action='skip'`, `reason` SHALL descrever em português por que a conversa foi pulada.

#### Scenario: Agente decide enviar em conversa padrão
- **GIVEN** conversa com handbook entregue ontem e cliente que demonstrou interesse mas não respondeu
- **WHEN** `decide_rewarm_action(conversation_id)` é chamada
- **THEN** o retorno SHALL ter `action='send'`
- **THEN** o retorno SHALL conter um campo `message` não vazio
- **THEN** o retorno SHALL conter um campo `reason` não vazio

#### Scenario: Agente pula quando cliente expressou desinteresse
- **GIVEN** conversa onde o cliente explicitamente disse "não quero mais" ou equivalente
- **WHEN** `decide_rewarm_action(conversation_id)` é chamada
- **THEN** o retorno SHALL ter `action='skip'`
- **THEN** o campo `reason` SHALL explicar que o cliente pediu para parar

#### Scenario: Agente pula quando cliente já comprou em outro lugar
- **GIVEN** conversa onde o cliente indicou que comprou curso equivalente em outro lugar
- **WHEN** `decide_rewarm_action(conversation_id)` é chamada
- **THEN** o retorno SHALL ter `action='skip'`
- **THEN** o campo `reason` SHALL mencionar a compra em outro lugar

#### Scenario: Mensagem respeita tom da conversa
- **GIVEN** conversa com operador usando tom informal e emojis
- **WHEN** `decide_rewarm_action(conversation_id)` retorna `action='send'`
- **THEN** a `message` produzida SHALL manter coerência com esse tom (verificado em teste qualitativo / snapshot contra prompt fixo)

### Requirement: Endpoint de preview dispara geração em paralelo
O sistema SHALL expor `POST /rewarm/preview` que, quando chamado, executa a query de candidatas, invoca `decide_rewarm_action` para cada uma em paralelo (com concorrência limitada), e retorna JSON com a lista completa de resultados incluindo `conversation_id`, `contact_name`, `phone_number`, `action`, `message` (quando send), `reason` e um identificador único por item (`item_id`) para uso posterior.

#### Scenario: Preview retorna lista ordenada de sugestões
- **GIVEN** três conversas candidatas com decisões mistas (send/send/skip)
- **WHEN** `POST /rewarm/preview` é chamado
- **THEN** o retorno SHALL ser HTTP 200
- **THEN** o corpo SHALL conter um array com 3 itens
- **THEN** cada item SHALL ter `item_id`, `conversation_id`, `action`, `reason`
- **THEN** itens com `action='send'` SHALL ter campo `message`

#### Scenario: Preview sem candidatas retorna lista vazia
- **GIVEN** zero conversas satisfazem o filtro
- **WHEN** `POST /rewarm/preview` é chamado
- **THEN** o retorno SHALL ser HTTP 200 com array vazio

#### Scenario: Preview requer autenticação de operador
- **GIVEN** requisição sem sessão válida
- **WHEN** `POST /rewarm/preview` é chamado
- **THEN** o sistema SHALL retornar HTTP 401

### Requirement: Endpoint de execução envia em batch com rate limit
O sistema SHALL expor `POST /rewarm/execute` que recebe uma lista de itens aprovados (cada um com `conversation_id`, `message` possivelmente editada) e dispara o envio em background. Os envios SHALL ser sequenciais com intervalo entre envios de `60 + uniform(-20, +40)` segundos (janela real 40–100s). Cada envio SHALL reusar `message_sender.send_message` (ou equivalente) para preservar registro em `messages`, anotação estratégica e indexação ChromaDB. Mensagens enviadas via rewarm SHALL ser marcadas em `sent_by` com valor distinto (ex: `rewarm_reviewed` quando passou por revisão humana, `rewarm_agent` quando disparada em modo automático).

#### Scenario: Execute enfileira envios e retorna imediatamente
- **GIVEN** lista com 3 itens aprovados
- **WHEN** `POST /rewarm/execute` é chamado
- **THEN** o retorno SHALL ser HTTP 202 (Accepted) imediatamente
- **THEN** os envios SHALL ocorrer em background

#### Scenario: Intervalo entre envios respeita janela configurada
- **GIVEN** execute rodando em background com 2 itens
- **WHEN** os envios são disparados
- **THEN** o delay entre o primeiro e o segundo envio SHALL ser `>=40s` e `<=100s`

#### Scenario: Item com mensagem editada envia o texto editado
- **GIVEN** item cujo `message` recebido difere do `message` gerado originalmente pelo agente
- **WHEN** o execute processa o item
- **THEN** a mensagem gravada em `messages` SHALL ser o texto editado

#### Scenario: Envio falho não interrompe o batch
- **GIVEN** item cujo envio via Evolution falha (timeout, 5xx)
- **WHEN** o batch processa o item
- **THEN** o sistema SHALL registrar o erro e SHALL continuar processando os itens restantes

#### Scenario: Mensagem enviada é atribuída ao rewarm
- **GIVEN** item aprovado e enviado via rewarm manual
- **WHEN** o registro é gravado em `messages`
- **THEN** o campo `sent_by` SHALL ser `'rewarm_reviewed'`

### Requirement: Flag de envio automático pula revisão
O sistema SHALL expor configuração `REWARM_AUTO_SEND` (booleano, default `false`) em `app/config.py`. Quando `REWARM_AUTO_SEND=true`, invocar o pipeline de rewarm (via endpoint dedicado ou invocação interna) SHALL gerar as sugestões e enviar automaticamente todas as que tiverem `action='send'`, sem passar pela tela de revisão. Mensagens enviadas nesse modo SHALL ter `sent_by='rewarm_agent'`.

#### Scenario: Modo automático ligado envia sem revisão
- **GIVEN** `REWARM_AUTO_SEND=true` e duas conversas candidatas, ambas com `action='send'`
- **WHEN** o pipeline é disparado (por endpoint automático ou invocação interna)
- **THEN** as duas mensagens SHALL ser enviadas em background com o mesmo rate limit
- **THEN** cada mensagem gravada SHALL ter `sent_by='rewarm_agent'`

#### Scenario: Modo automático respeita decisões de skip
- **GIVEN** `REWARM_AUTO_SEND=true` e uma conversa para a qual o agente decidiu `action='skip'`
- **WHEN** o pipeline é disparado
- **THEN** nenhuma mensagem SHALL ser enviada para essa conversa
- **THEN** o `reason` do skip SHALL ser logado

#### Scenario: Modo manual ignora a flag e sempre retorna preview
- **GIVEN** `REWARM_AUTO_SEND=true` mas operador clicou no botão manualmente (via `POST /rewarm/preview`)
- **WHEN** o preview é processado
- **THEN** o sistema SHALL retornar a lista de sugestões normalmente sem enviar nada automaticamente

### Requirement: Tela de revisão permite editar e enviar em batch
O sistema SHALL apresentar, ao clicar em "Reesquentar D-1", uma interface modal ou página dedicada listando os resultados do preview. A interface SHALL permitir ao operador: (i) ver o texto da mensagem sugerida para cada item `send`, (ii) editar o texto inline, (iii) remover itens individualmente do batch, (iv) ver os itens `skip` com suas razões, (v) disparar o envio em batch de todos os itens restantes.

#### Scenario: Operador edita mensagem antes de enviar
- **GIVEN** preview com item gerado pelo agente
- **WHEN** o operador edita o texto no campo da tela e clica "Enviar todos"
- **THEN** a chamada a `/rewarm/execute` SHALL incluir a mensagem editada para aquele item

#### Scenario: Operador remove item do batch
- **GIVEN** preview com 3 itens
- **WHEN** o operador remove um item e clica "Enviar todos"
- **THEN** `/rewarm/execute` SHALL receber 2 itens (o removido não participa)

#### Scenario: Itens skipados são exibidos mas não enviáveis
- **GIVEN** preview contém 2 itens `send` e 1 item `skip`
- **WHEN** a tela é renderizada
- **THEN** o item `skip` SHALL ser visível com sua razão
- **THEN** o item `skip` SHALL NOT ter botão/campo para envio

### Requirement: Botão "Reesquentar D-1" dispara o fluxo
O sistema SHALL disponibilizar um botão com rótulo claro de "Reesquentar D-1" (ou equivalente) na interface do operador, acessível a partir da tela principal. O botão SHALL disparar `POST /rewarm/preview`, mostrar estado de loading enquanto aguarda resposta, e abrir a tela de revisão quando o preview retornar.

#### Scenario: Clique dispara preview e abre revisão
- **GIVEN** operador logado na tela principal
- **WHEN** o operador clica em "Reesquentar D-1"
- **THEN** o sistema SHALL chamar `POST /rewarm/preview`
- **THEN** SHALL mostrar indicador de loading
- **THEN** SHALL abrir a tela de revisão com os resultados quando a resposta chegar

#### Scenario: Preview vazio mostra mensagem amigável
- **GIVEN** preview retornou zero candidatas
- **WHEN** a tela de revisão seria aberta
- **THEN** o sistema SHALL exibir mensagem indicando que não há conversas elegíveis no momento

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

