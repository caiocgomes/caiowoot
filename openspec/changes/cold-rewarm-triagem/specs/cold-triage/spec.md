## Capability: cold-triage

### Propósito

Dado o pool de leads do curso CDO que entraram em `handbook_sent` ou `link_sent` há mais de 30 dias e não voltaram, selecionar os mais recuperáveis, classificar a objeção implícita de saída, decidir ação (mentoria / conteudo / skip) via matriz determinística e compor mensagem personalizada no tom do operador, tudo em batch de até 20 candidatos por acionamento manual.

### Invariantes

- I1. **Negativa explícita nunca é tocada.** Se o classificador retorna `negativo_explicito` ou se `conversations.cold_do_not_contact=1`, a ação é obrigatoriamente skip.
- I2. **Baixa confiança força skip.** Se o classificador retorna `confidence='low'`, a ação é skip, independente da classification.
- I3. **Cooldown de 90 dias.** Conversa que recebeu cold_dispatch com status em (`sent`, `approved`, `previewed`) nos últimos 90 dias não entra em novo pool.
- I4. **Cap de mentoria é respeitado.** Quantidade de dispatches com `action='mentoria'` e status em (`sent`, `approved`) no mês local corrente não pode ultrapassar `cold_mentoria_monthly_cap`. Quando atinge, novas recomendações de mentoria são rebaixadas para conteudo (link_sent) ou skip (handbook_sent).
- I5. **Ordem importa.** Prioridade de envio: link_sent com timing+citação de retorno > link_sent com outras objeções > handbook_sent com timing > demais.
- I6. **Citação literal é obrigatória quando há.** Compositor recebe no prompt a citação literal do lead e tem que incorporá-la na mensagem (ou rephrasing próximo com marcador temporal).
- I7. **Tom não negociável.** Minúsculas dominantes, sem em-dash, primeira pessoa, sem performance de venda, opcionalmente um fat-finger sutil.
- I8. **Idempotência do preview.** Clicar preview duas vezes no mesmo dia gera dois conjuntos de dispatch `previewed`. Os `previewed` não contam no cap de mentoria (só `sent`/`approved`).
- I9. **Resposta fecha automaticamente o hot flow.** Quando lead responde qualquer coisa a um cold_dispatch recente, `responded_at` é marcado mas a conversa flui pra operadores normalmente; cold rewarm não tenta classificar resposta nem gerar follow-up.

### Especificação operacional

#### Classificação

Entrada: `conversation_id`.
Processo: Haiku lê histórico completo, retorna via tool `cold_classify` o objeto `{classification, confidence, quote_from_lead, reasoning}`.

Domínio de `classification`:
- `objecao_preco`: lead reagiu negativamente a preço ou questionou valor.
- `objecao_timing`: lead sinalizou que retorna depois (prazo, vida, próximo mês).
- `objecao_conteudo`: lead tem dúvida específica não resolvida sobre escopo/conteúdo.
- `tire_kicker`: lead pediu handbook ou link sem engajamento, silenciou imediatamente.
- `negativo_explicito`: lead pediu pra parar, foi hostil, disse que não quer.
- `perdido_no_ruido`: silenciou sem sinal claro de objeção.
- `nao_classificavel`: nada acima cabe com confiança.

Domínio de `confidence`: `high | med | low`.

#### Matriz de ação

Quando `mentoria_used < cold_mentoria_monthly_cap` e `confidence in (high, med)`:

| classification      | link_sent  | handbook_sent |
|---------------------|------------|---------------|
| objecao_preco       | mentoria   | skip          |
| objecao_timing      | mentoria   | mentoria      |
| objecao_conteudo    | mentoria   | conteudo      |
| tire_kicker         | skip       | skip          |
| negativo_explicito  | skip       | skip          |
| perdido_no_ruido    | conteudo   | skip          |
| nao_classificavel   | skip       | skip          |

Quando `mentoria_used >= cap`, células `mentoria` viram `conteudo` para link_sent e `skip` para handbook_sent. Quando `confidence='low'`, toda célula vira `skip`.

#### Composição

Entrada: conversation_id, action, classification, quote_from_lead, contact_name.
Processo: Haiku com tool `cold_compose_message` recebe histórico resumido + quote + ação. Retorna `{message}` string.

Oferta embutida por ação:
- `mentoria`: menciona sessão privada 1h com o Caio, janela aberta por tempo limitado.
- `conteudo`: referência à série recente de posts (ou conteúdo relevante), sem oferta comercial.

#### Preview e execução

`POST /cold-rewarm/preview`:
- Seleciona até 80 candidatos (cooldown, filtros, ordenação por estágio e frescor).
- Classifica todos em paralelo.
- Calcula `mentoria_used` do mês.
- Aplica matriz por item (alocando mentorias conforme cap).
- Compõe mensagens para items com ação ≠ skip.
- Reordena por score final e corta em 20.
- Grava cada item como `cold_dispatches` com `status='previewed'`.
- Retorna JSON array ao frontend.

`POST /cold-rewarm/execute`:
- Payload: `{items: [{dispatch_id, message}]}` onde `message` pode ter sido editada.
- Background task dispara envios sequenciais com delay uniforme em [40s, 100s].
- Para cada item: chama `send_and_record` com operator `cold_rewarm`, atualiza `cold_dispatches.message_sent`, `scheduled_send_id`, `status='sent'`. Falha vira `status='failed'`.
- Retorna 202 imediatamente.

### Requisitos não-funcionais

- **R1. Tempo de preview:** < 90s para batch de 80 candidatos (limite prático do botão).
- **R2. Custo por batch:** < US$ 0.30 em Haiku (classificação + composição).
- **R3. Rate limit de envio:** conforme D-1 existente, intervalo entre envios uniforme em [40s, 100s], sem cap de throughput do sistema.
- **R4. Observabilidade:** cada decisão do classificador e matriz é persistida em `cold_dispatches` com campo `reasoning` separado pra auditoria posterior.
