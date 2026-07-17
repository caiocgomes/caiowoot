## ADDED Requirements

### Requirement: Seleção de candidatos cold (+30 dias)
O sistema SHALL selecionar como candidatos a cold rewarm conversas com `funnel_product='curso-cdo'`, última mensagem (qualquer direção) há mais de 30 dias, `conversations.cold_do_not_contact = 0`, e sem `cold_dispatch` com status em (`sent`, `approved`) nos últimos 90 dias. O `funnel_stage` armazenado NÃO SHALL filtrar candidatos; o estágio real é inferido pelo classificador a partir do histórico.

#### Scenario: Lead com última inbound há 40 dias e nunca tocado entra no pool
- **GIVEN** conversa CDO com última mensagem há 40 dias e nenhum cold_dispatch anterior
- **WHEN** `select_cold_candidates` executa
- **THEN** a conversa SHALL aparecer no resultado

#### Scenario: Lead com cold_dispatch sent há 60 dias fica fora do pool
- **GIVEN** conversa CDO elegível por tempo mas com cold_dispatch sent há 60 dias
- **WHEN** `select_cold_candidates` executa
- **THEN** a conversa SHALL NOT aparecer (cooldown ativo)

#### Scenario: Lead com cold_dispatch apenas previewed (nunca enviado) continua elegível
- **GIVEN** conversa CDO com cold_dispatch status='previewed' (rascunho não enviado)
- **WHEN** `select_cold_candidates` executa
- **THEN** a conversa SHALL aparecer (cooldown só conta sent/approved)

#### Scenario: Lead com cold_do_not_contact=1 nunca aparece
- **GIVEN** conversa marcada como `cold_do_not_contact=1`
- **WHEN** `select_cold_candidates` executa
- **THEN** a conversa SHALL NOT aparecer independente dos outros critérios

### Requirement: Classificação da objeção via Haiku com stage_reached
O sistema SHALL chamar o Haiku para cada candidato, retornando via tool `cold_classify` os campos: `classification` ∈ {`ja_comprou`, `abandono_checkout`, `objecao_preco`, `objecao_timing`, `objecao_conteudo`, `tire_kicker`, `negativo_explicito`, `perdido_no_ruido`, `nao_classificavel`}, `stage_reached` ∈ {`link_sent`, `handbook_sent`, `only_qualifying`, `nunca_qualificou`}, `confidence` ∈ {`high`, `med`, `low`}, `quote_from_lead` (frase literal), e `reasoning` (1-2 frases).

#### Scenario: Lead que verbalizou pedido do link e sumiu após receber vira abandono_checkout
- **GIVEN** histórico onde operador enviou link de pagamento após lead escrever "me manda o link"
- **WHEN** o classificador é chamado
- **THEN** `classification` SHALL ser `abandono_checkout` e `stage_reached` SHALL ser `link_sent`

#### Scenario: tire_kicker nunca coexiste com stage_reached=link_sent
- **GIVEN** conversa com outbound do operador contendo URL de checkout
- **WHEN** o classificador é chamado
- **THEN** `tire_kicker` SHALL NOT ser o valor de `classification`

#### Scenario: Hostilidade vira negativo_explicito com confidence high
- **GIVEN** lead escreveu "me tira daí" ou variação
- **WHEN** o classificador é chamado
- **THEN** `classification` SHALL ser `negativo_explicito` e `confidence` SHALL ser `high`

### Requirement: Matriz determinística classifica ação
O sistema SHALL mapear `(classification, stage_reached)` para uma ação ∈ {`mentoria`, `conteudo`, `skip`} via matriz determinística. `negativo_explicito` e `ja_comprou` sempre viram `skip`. `link_sent` é tratado agressivamente: todas as classificações (exceto negativo_explicito e ja_comprou) viram `mentoria`, com fallback para `perdido_no_ruido` quando confidence=low. Cap mensal de mentoria (default 15, via `settings.cold_mentoria_monthly_cap`) rebaixa ações `mentoria` para `conteudo` (link_sent, handbook_sent) ou `skip` (only_qualifying, nunca_qualificou) quando atingido.

#### Scenario: abandono_checkout × link_sent vira mentoria
- **WHEN** `apply_matrix(classification='abandono_checkout', stage='link_sent', mentoria_used=0, cap=15, confidence='high')`
- **THEN** a ação SHALL ser `mentoria`

#### Scenario: Cap de mentoria atingido rebaixa para conteudo em link_sent
- **WHEN** `apply_matrix('abandono_checkout', 'link_sent', mentoria_used=15, cap=15, confidence='high')`
- **THEN** a ação SHALL ser `conteudo`

#### Scenario: ja_comprou sempre skip independente de stage ou cap
- **WHEN** `apply_matrix('ja_comprou', qualquer_stage, mentoria_used=*, cap=*, confidence=*)`
- **THEN** a ação SHALL ser `skip`

#### Scenario: Low confidence em stage forte vira perdido_no_ruido e cai na matriz
- **WHEN** `apply_matrix('nao_classificavel', 'link_sent', mentoria_used=0, cap=15, confidence='low')`
- **THEN** a classification SHALL ser rebaixada para `perdido_no_ruido` e a ação final SHALL ser `mentoria` (via matriz)

#### Scenario: Low confidence em stage fraco força skip
- **WHEN** `apply_matrix('objecao_timing', 'nunca_qualificou', mentoria_used=0, cap=15, confidence='low')`
- **THEN** a ação SHALL ser `skip`

### Requirement: Composição de mensagem no tom Caio
O sistema SHALL chamar o Haiku via tool `cold_compose_message` para ações `mentoria` ou `conteudo`, passando conversation_id, action, classification, quote_from_lead e contact_name. A mensagem retornada SHALL seguir o tom Caio (minúsculas dominantes, sem em-dash, primeira pessoa, citação literal do lead com marcador temporal vago, fat-finger sutil ocasional). Para mensagens com ação `conteudo`, o compositor inclui placeholder `[link]` para o operador preencher.

#### Scenario: Compositor inclui a citação no prompt
- **WHEN** `compose_message(action='mentoria', quote_from_lead='mes que vem volto', ...)` é chamado
- **THEN** o user content passado ao Haiku SHALL conter a string "mes que vem volto"

#### Scenario: Falha do Haiku retorna string vazia
- **WHEN** o cliente Anthropic levanta exceção
- **THEN** `compose_message` SHALL retornar string vazia sem levantar

### Requirement: Proteção contra toque em quem já comprou
Quando o classificador retorna `ja_comprou` com confidence=high, o sistema SHALL marcar `conversations.cold_do_not_contact=1` automaticamente, banindo o lead permanentemente do pool. Confidence=med ou low em ja_comprou SHALL resultar em skip apenas para a execução atual, sem ban.

#### Scenario: ja_comprou high confidence bane o lead
- **GIVEN** classificador retorna `{classification: 'ja_comprou', confidence: 'high'}`
- **WHEN** `run_preview` processa o candidato
- **THEN** `conversations.cold_do_not_contact` SHALL ser atualizado para 1 nessa conversa

#### Scenario: ja_comprou med confidence não bane
- **GIVEN** classificador retorna `{classification: 'ja_comprou', confidence: 'med'}`
- **WHEN** `run_preview` processa o candidato
- **THEN** a ação SHALL ser skip mas `cold_do_not_contact` SHALL permanecer 0

### Requirement: Endpoints POST /cold-rewarm/preview e /cold-rewarm/execute
O sistema SHALL expor `POST /cold-rewarm/preview` retornando até 20 items com dispatch_id, conversation_id, phone_number, contact_name, funnel_stage, stage_reached, classification, confidence, quote_from_lead, reasoning, action, message, days_cold. Cada item SHALL ser persistido em `cold_dispatches` com status='previewed'. O endpoint `POST /cold-rewarm/execute` SHALL receber `{items: [{dispatch_id, conversation_id, message}]}`, disparar batch assíncrono com rate limit 40-100s por envio, e retornar HTTP 202.

#### Scenario: Preview sem candidatos retorna lista vazia
- **GIVEN** nenhuma conversa elegível
- **WHEN** `POST /cold-rewarm/preview`
- **THEN** a resposta SHALL ser HTTP 200 com array vazio

#### Scenario: Execute dispara batch e retorna 202
- **GIVEN** items aprovados no modal
- **WHEN** `POST /cold-rewarm/execute` com payload válido
- **THEN** a resposta SHALL ser HTTP 202 imediato e a task de envio SHALL ser disparada em background

### Requirement: Hook de reward marca responded_at
Quando uma inbound chega em uma conversa com `cold_dispatches` em status='sent' recente (<7 dias) e responded_at null, o sistema SHALL marcar `responded_at` no dispatch. Não há classificação produtiva/tóxica; qualquer resposta conta.

#### Scenario: Inbound em conversa com dispatch recente marca resposta
- **GIVEN** conversa com cold_dispatch sent há 2 horas e responded_at null
- **WHEN** uma inbound chega via webhook
- **THEN** `cold_dispatches.responded_at` SHALL ser preenchido com o timestamp da inbound

#### Scenario: Inbound em dispatch antigo (>7 dias) não marca
- **GIVEN** conversa com cold_dispatch sent há 10 dias
- **WHEN** uma inbound chega
- **THEN** responded_at SHALL permanecer null (janela de reward expirou)

### Requirement: UI com botão Cold Rewarm e modal de revisão
A UI SHALL apresentar um botão "Cold Rewarm" na sidebar ao lado do "Reesquentar leads". Clique dispara `POST /cold-rewarm/preview` e abre um modal mostrando, por item: nome, telefone, chips de estágio/classificação/confiança/dias frio, citação literal, ação recomendada, textarea editável da mensagem. Items com action=skip aparecem em seção separada com reasoning. Nomes são links clicáveis que abrem a conversa. Botão "Enviar todos" dispara `POST /cold-rewarm/execute`.

#### Scenario: Pulados mostram reasoning
- **WHEN** o modal renderiza items com action='skip'
- **THEN** cada skip SHALL exibir chips de classificação/confiança, citação e reasoning do Haiku

#### Scenario: Clique no nome abre conversa
- **WHEN** operador clica no nome de um item (send ou skip)
- **THEN** o modal SHALL fechar e a conversa correspondente SHALL abrir via `openConversation(id)`
