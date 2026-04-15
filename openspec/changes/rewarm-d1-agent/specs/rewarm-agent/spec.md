## ADDED Requirements

### Requirement: Query de conversas candidatas a reesquentamento D-1
O sistema SHALL selecionar como candidatas a reesquentamento D-1 exatamente as conversas que, no momento do clique, satisfazem todos os critérios: `funnel_product = 'curso-cdo'`, `funnel_stage IN ('handbook_sent', 'link_sent')`, existe ao menos uma mensagem em `messages` cuja `DATE(created_at)` é igual a `DATE('now','-1 day')`.

#### Scenario: Conversa elegível é incluída
- **GIVEN** conversa com `funnel_product='CDO'`, `funnel_stage='handbook_sent'`, ao menos uma mensagem criada ontem, e sem draft pendente
- **WHEN** o sistema executa a query de candidatas
- **THEN** a conversa SHALL aparecer no resultado

#### Scenario: Conversa com produto diferente é excluída
- **GIVEN** conversa com `funnel_product='outro-curso'` e demais critérios atendidos
- **WHEN** o sistema executa a query de candidatas
- **THEN** a conversa SHALL NOT aparecer no resultado

#### Scenario: Conversa em stage diferente é excluída
- **GIVEN** conversa com `funnel_product='CDO'`, `funnel_stage='qualifying'`, mensagem ontem, sem draft pendente
- **WHEN** o sistema executa a query de candidatas
- **THEN** a conversa SHALL NOT aparecer no resultado

#### Scenario: Conversa sem mensagem em D-1 é excluída
- **GIVEN** conversa com `funnel_product='CDO'`, `funnel_stage='link_sent'`, última mensagem há 3 dias, sem draft pendente
- **WHEN** o sistema executa a query de candidatas
- **THEN** a conversa SHALL NOT aparecer no resultado

#### Scenario: Conversa com draft pendente continua incluída
- **GIVEN** conversa que satisfaz product/stage/mensagem-D-1 e possui um draft com `status='pending'`
- **WHEN** o sistema executa a query de candidatas
- **THEN** a conversa SHALL aparecer no resultado (safeguard removido por decisão do operador em 2026-04-15)

#### Scenario: Conversa já purchased é excluída
- **GIVEN** conversa com `funnel_stage='purchased'` mesmo tendo sido `handbook_sent` ou `link_sent` em algum momento
- **WHEN** o sistema executa a query de candidatas
- **THEN** a conversa SHALL NOT aparecer no resultado

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
