## Context

O rewarm D-1 existente trata leads que esfriaram em 24h (lembrete barato). Cold rewarm é problema diferente: leads a 30+ dias de distância, muitas vezes com objeção implícita na última conversa (preço, timing, conteúdo). Triagem manual em ~200 conversas é inviável, então o Haiku vira o triagista e o compositor, com a matriz determinística atuando como guard-rail entre classificação e ação. A UX copia o padrão do D-1 (preview → revisão modal → execute batch) porque é mental model conhecido do operador.

## Decisões-chave

### D1. Duas chamadas Haiku por candidato em vez de uma

Chamada 1: classifica objeção + confiança + citação literal. Chamada 2: compõe mensagem condicional à ação decidida pela matriz. Separar é mais honesto analiticamente (classificação registrada independentemente da mensagem; podemos medir acerto do classificador) e permite logar decisões sem precisar enviar. Custo: ~2x tokens por lead vs uma chamada. 20 leads × 2 chamadas ~= US$ 0.05 por batch. Irrelevante.

Alternativa rejeitada: uma chamada só com tool ampla que devolve `{classification, action, message}`. Simples mas mistura diagnóstico e tratamento num fluxo só, dificulta debug e limita a introdução da matriz determinística como guard-rail.

### D2. Matriz determinística entre classificação e ação

Por que não deixar Haiku escolher a ação? Duas razões. Uma, a escolha da ação depende de estado externo (cap mensal de mentoria já consumido), que o Haiku não vê. Duas, queremos garantir contratualmente que tire-kicker e negativo explícito sempre pulam, sem depender de julgamento do modelo. A matriz é código, testável, auditável.

### D3. Cap mensal de mentoria como fonte única da verdade

Mentoria é recurso escasso (Caio faz 1h individual). Cap default 15/mês, configurável via env. Contagem baseada em `cold_dispatches` com `action='mentoria'` e `created_at` no mês atual (não depende de o lead ter aceitado; conta oferta, não entrega, pra ser conservador com a agenda).

Quando atinge cap durante um batch: link_sent vira conteudo, handbook_sent vira skip. O compositor recebe a ação já decidida; não sabe nem tenta oferecer mentoria fora do cap.

### D4. Priorização na seleção

Na query de candidatos, ordena por score desc onde score é: estágio link_sent vale mais que handbook_sent; classificação "timing" com citação contendo "volto"/"mês que vem"/"depois"/"retomo" vale mais; dias-desde-última-mensagem quanto menor melhor. Isso pode ser feito com uma só passagem Haiku + classificação SQL grosseira, ou em duas fases (query bruta primeiro, depois classifica, depois re-ordena). Escolha: **duas fases**, porque o score fino exige a classificação. Primeiro SELECT amplo (até 80 candidatos ordenados por link_sent DESC, dias_frio ASC), depois classifica todos, depois reordena por score final e corta em 20.

Custo: 80 classificações Haiku por batch (~US$ 0.10). Tempo: ~30-60s com paralelismo via gather. Aceitável pro botão manual.

### D5. Tom "Caio digitando"

Características que o prompt do compositor tem que fixar:
- minúsculas dominantes (aceita maiúscula em nome próprio e início de parágrafo se soar natural, mas default lowercase).
- zero em-dash (regra global do usuário). Zero travessão duplo, zero "—".
- primeira pessoa direta ("oi, o caio aqui", "lembrei de você", "abri").
- citação literal do lead com marcador temporal vago ("você me disse em junho", "lá em julho você falou").
- mencionar a janela aberta de forma explícita mas sem teatro ("abri algumas vagas", "consegui abrir uma janela pra isso").
- um fat-finger sutil em ~20% das mensagens (trocar uma letra, omitir acento, tipo "obirgado", "valeu pela paciencia"). Não pode virar paródia, só textura.
- não brincar, não usar emoji desnecessariamente, não fazer consultoria de marketing. Direto.

O prompt do compositor vai em `COLD_COMPOSE_SYSTEM_PROMPT` em `cold_triage.py`.

### D6. Cooldown de 90 dias na mesma conversa

Se a conversa recebeu cold rewarm recente (qualquer status exceto skipped), não entra no pool de novo por 90 dias. Proteção contra chamar 2x a mesma pessoa num mesmo backlog, que é a pior queima possível. Checagem feita na query.

### D7. UX: modal similar ao D-1, campos novos

Campos por item no modal:
- nome + telefone + estágio (herdado do D-1)
- classificação inferida e confiança (novo)
- citação literal do lead que sustentou a classificação (novo, ajuda operador a auditar)
- ação recomendada (mentoria / conteudo); skips ficam em seção separada como no D-1
- rascunho da mensagem editável
- botão remover

### D8. Execução com rate limit próprio

`execute_batch` replica a lógica de `next_delay()` do rewarm_engine (60s + uniform(-20, +40) = janela 40-100s) mas localmente, sem depender de importação. Envio sequencial direto via `send_and_record`, atualização de `cold_dispatches` por item. Falha parcial não aborta o batch; item falho vai pra status='failed', demais continuam.

Alternativa que não vale: distribuir em janelas 12:30/18:30 via bandit do D-1. Sobrepõe responsabilidades. Se quiser isso depois, migra pra `scheduled_sends`.

### D9. Reward = responder (qualquer resposta)

V1 não classifica resposta produtiva/tóxica. Se o lead respondeu, o fluxo hot normal atende. Operador decide qualidade. Instrumentação ainda grava `responded_at` em `cold_dispatches` via hook do webhook (já existe padrão em `rewarm_bandit.handle_reward_inbound`), mas sem classificação Haiku separada. Relatório mostra só responde/não responde.

### D10. Sem cron, botão apenas

V1 é 100% manual. Quando o comportamento estabilizar (tipicamente 2-3 batches), change separada adiciona cron diário/semanal e opcionalmente distribuição em janelas do bandit.

## Arquitetura de execução

```
OPERADOR clica "Cold Rewarm"
    │
    ▼
POST /cold-rewarm/preview
    │
    ▼
cold_triage.run_preview(limit=20):
    1. candidatos = select_cold_candidates(db)  ~80 linhas
    2. classifications = gather(classify_conversation(c) for c in candidatos)
    3. mentoria_used = count_mentoria_offers_this_month(db)
    4. para cada cand + classif:
         action = apply_matrix(classif, stage, mentoria_used, cap)
         se action == mentoria: mentoria_used += 1
         se action in (skip/descartar): marca e continua
         se action == mentoria ou conteudo:
             message = compose_message(cand, action, classif)
    5. reordena por score, corta top 20, grava previews em cold_dispatches
       (status='previewed'), retorna JSON
    │
    ▼
MODAL renderiza; operador edita/remove, clica "Enviar todos"
    │
    ▼
POST /cold-rewarm/execute {items: [{conversation_id, message, dispatch_id}]}
    │
    ▼
Background task: execute_batch com asyncio.sleep(next_delay()) a cada item
    - pra cada item: send_and_record direto (infra de send_executor)
    - update cold_dispatches.message_sent e status='sent' (ou 'failed')
    - scheduled_send_id fica null na v1 (campo preparado pra evolução futura)
    │
    ▼
Webhook inbound (hook mark_cold_response_received): ao receber inbound de conv
    com cold_dispatch status='sent' e updated_at <7d sem responded_at →
    marca responded_at. Não classifica (reward é só boolean).
```

## Cuidados operacionais

1. **Idempotência do preview**: operador pode recarregar modal, mas cada clique faz novo preview completo (consome Haiku). Alternativa seria cachear 15 min, mas não vale a complexidade pra uso esporádico.
2. **Fila de envio simultânea**: se operador dispara cold rewarm e D-1 no mesmo dia, os dois usam `run_batch` sequencial em tasks separadas. Rate limit não é compartilhado — pode ter dois envios em janela sobreposta. Aceitável pro volume; monitorar.
3. **Cap de mentoria não é transacional**: decremento lógico acontece durante a montagem do preview, não no commit. Se o operador rodar preview, desistir, rodar de novo no mesmo dia, vai re-contar. Proteção contra isso: cap é "oferta já apresentada ao Caio", e se ele aprovar o execute, o registro grava. Se reapresenta preview, o Haiku vê os dispatches `status='previewed'` anteriores como não-contabilizados? Decisão: sim, `count_mentoria_offers_this_month` conta apenas `status in ('sent', 'approved')`, não `previewed`. Preview é descartável.
4. **Mensagem editada no modal**: se o operador editar a mensagem antes de enviar, grava a editada em `message_sent` (não a original do Haiku). Original fica em `message_draft` pra auditoria.
5. **Cooldown vs negativa explícita**: cooldown de 90 dias vale pra qualquer status. Negativa explícita seta uma flag `cold_do_not_contact=1` em `conversations` (migration adiciona coluna). Essa flag vale permanente; cooldown é só temporal.
6. **Falha parcial no envio**: se uma mensagem do batch falhar, as demais continuam. Dispatch com falha fica com `status='failed'`. Relatório agrega falhas.

## O que NÃO está neste change

- Cron diário automático (entra em change subsequente).
- Distribuição em janelas 12:30/18:30 via bandit (idem).
- Classificação produtiva/tóxica da resposta (o fluxo hot normal já cobre).
- Onda 2 (oferta após conteúdo da onda 1). V1 é toque único.
- Downsell (não existe curso mais barato no catálogo).
- Dashboard dedicado. Relatório é consulta SQL simples.
- Extensão a outros produtos (só CDO).
