## Context

O CaioWoot já tem todas as peças para construir esse agente: modelo de dados de conversas/mensagens com funnel, `claude_client` para chamar Haiku, `message_sender` que grava e dispara Evolution API, e padrão de tela/modal no frontend. O desafio é composicional: orquestrar "ler conversa → decidir → revisar → enviar em batch com rate limit" e deixar o caminho pronto para virar automático sem refactor. Os primeiros dias são de operação tutelada — o operador aperta o botão, revisa as sugestões, envia. A expectativa é que em poucos dias a flag `REWARM_AUTO_SEND` seja ligada e um cron assuma.

## Goals / Non-Goals

**Goals:**
- Agente autônomo que gera mensagens de reesquentamento contextualizadas por conversa (tom espelhado do histórico).
- Preview único e transiente pós-clique (sem fila persistente, sem drafts no banco).
- Envio em batch com rate limit anti-spam (jitter aleatório) reusando `message_sender`.
- Flag de configuração que transforma o pipeline em totalmente autônomo sem mudança de código.
- Agente pode retornar `skip` com razão quando o histórico indica que reesquentar pioraria a conversa.

**Non-Goals:**
- Tabela de histórico de transições de `funnel_stage` (decidido contra — query pelo estado atual + última mensagem em D-1 cobre o caso).
- Taxonomia explícita de objeções do CDO (agente decide livremente).
- Persistência da fila de revisão (transiente; fechou aba, aperta de novo).
- Cron/scheduler automatizado (o arcabouço fica pronto via flag, mas o job agendado é fora de escopo).
- Dashboard próprio de métricas de rewarm (roda no fluxo de `operator_coaching` existente).
- Telas de edição em massa ou funcionalidades de filtro avançado no preview.

## Decisions

### D1 — Filtro SQL "sem histórico de transição"
Query candidata filtra por `funnel_product = 'curso-cdo'`, `funnel_stage IN ('handbook_sent', 'link_sent')`, e **a última mensagem da conversa foi em D-1** (i.e., `DATE(MAX(messages.created_at)) = DATE('now','-1 day')`). A versão inicial usava `EXISTS mensagem em D-1`, que incluía conversas que tiveram msg ontem E também hoje — mas essas estão ativas, não são alvo. **O safeguard de "sem draft pendente" foi removido por decisão do operador** (2026-04-15): estava excluindo conversas válidas em produção. Se o agente mandar rewarm em conversa com draft pendente, o pior caso é um draft ficar obsoleto — o operador descarta na tela.

**Alternativa considerada:** tabela `funnel_stage_transitions` para registrar a data exata da transição. Rejeitada — aumenta escopo (migração + hooks em dois lugares) sem benefício material dado que a heurística "houve mensagem em D-1 + stage atual é handbook/link" captura o alvo real. Se ficar impreciso com uso, criar tabela depois.

### D2 — Agente decide skip com razão
A função `decide_rewarm_action(conversation_id)` retorna um dict `{action: 'send'|'skip', message?: str, reason: str}`. O prompt do agente inclui explicitamente a permissão de pular quando o histórico sugere: cliente explicitou desinteresse, comprou em outro lugar, hostilidade no atendimento, ou já houve reesquentamento recente na própria conversa.

**Alternativa considerada:** sempre mandar, confiando no filtro SQL. Rejeitada — o SQL é grosso; o agente é o único lugar que lê o teor semântico da conversa. Sem poder de skip, o feature mandaria follow-ups pra gente que pediu pra parar, o que é pior que não ter feature.

### D3 — Prompt espelha o tom da conversa
O prompt instrui o agente a identificar o tom natural da conversa (formal/informal, uso de emoji, extensão de mensagem do operador, gírias) e produzir UMA mensagem nesse tom. Sem variações, sem tons fixos (direto/consultivo/casual do draft_engine).

**Alternativa considerada:** 3 drafts como no draft_engine. Rejeitada — em massa isso é 3× o custo de revisão e de API. A escolha editorial ("como reesquentar") é específica demais pra oferecer 3 tons genéricos.

### D4 — Pipeline único com flag de gate no final
O mesmo endpoint de geração (`POST /rewarm/preview`) é chamado pelo frontend manual e pelo futuro cron. A diferença é apenas o que acontece depois: modo manual → retorna lista pra UI + chama `/rewarm/execute` com as aprovações. Modo automático (`REWARM_AUTO_SEND=true`) → chama `execute` direto internamente com tudo que não deu skip.

**Alternativa considerada:** dois pipelines separados (manual vs automático). Rejeitada — duplica código e garante que, quando ligar a flag, surjam divergências de comportamento.

### D5 — Rate limit inline em `/rewarm/execute` com `asyncio.sleep`
O execute roda como background task: itera a lista aprovada, para cada item chama `message_sender.send`, depois `asyncio.sleep(60 + uniform(-20, +40))` antes do próximo. Janela real 40–100s entre envios.

**Alternativa considerada:** usar o `campaign_executor` existente (fila + polling 10s). Rejeitada para o MVP — o campaign_executor é acoplado ao modelo `campaigns` (CSV + imagem + retry), adaptá-lo pra enfileirar itens avulsos adiciona complexidade. Se o volume crescer ou quisermos retry robusto, migra depois.

### D6 — Preview transiente; sem persistência
O endpoint `/rewarm/preview` roda a geração dos agentes em paralelo e devolve a lista completa como JSON. Se o operador fechar a aba sem executar, os resultados são perdidos — nova chamada regera. Sem tabela nova, sem TTL.

**Alternativa considerada:** tabela `rewarm_queue` com TTL. Rejeitada — essa feature "vai morrer" em 4 dias virando automática; persistir fila é over-engineering.

### D7 — ~~Safeguard contra encavalamento~~ (removido)
Versão original filtrava `NOT EXISTS drafts pendentes` para evitar duplo clique e encavalamento com engajamento ativo. **Removido em 2026-04-15** após rodar em produção — estava excluindo conversas válidas (alguns leads CDO acumulam drafts pending mesmo sendo alvo legítimo de rewarm). Duplo clique segue coberto pelo loading state no front; encavalamento fica como responsabilidade do operador na tela de revisão (ele vê o histórico e decide).

### D8 — Telemetria via análise geral existente
Mensagens enviadas pelo agente ficam em `messages` com `direction='outbound'` e `sent_by` identificando origem do rewarm (ex: `sent_by='rewarm_agent'` ou `sent_by='rewarm_reviewed'`). O `conversation_analysis.py` já varre conversas e avalia qualidade; basta estendê-lo minimamente para considerar mensagens de rewarm no agregado. Sem dashboard novo.

### D9 — Configuração via env var
`REWARM_AUTO_SEND` vive em `app/config.py` como booleano lido de env. Default `false`. Mudança de estado não precisa de deploy de código — só restart com env atualizada.

## Risks / Trade-offs

- **[Agente manda mensagem inadequada em produção com automático ligado]** → Mitigação: os 4 dias de operação manual são instrumentais para calibrar o prompt. Além disso, `conversation_analysis` post-envio detecta degradação no agregado. Se ficar preocupante, adicionar sample manual aleatório (1/N) como review opcional.

- **[Query fica cara em escala]** → Mitigação: o filtro roda só quando o botão é apertado (ou 1x/dia no cron futuro). Com índices existentes em `conversations(funnel_product)` e `messages(conversation_id, created_at)` (verificar se existem; se não, criar), performance é trivial mesmo com milhares de conversas.

- **[Custo de API desperdiçado se operador fecha aba sem executar]** → Mitigação aceita. Haiku é barato; o comportamento esperado é apertar, revisar, executar em minutos.

- **[Double-click durante geração (antes do preview voltar)]** → Mitigação: frontend trava o botão no estado de loading até resposta chegar. Backend pode tolerar: a segunda chamada simplesmente regera e devolve outra lista.

- **[`funnel_stage` é inferido pelo LLM — pode estar errado]** → Mitigação aceita. Se `situation_summary` classificou mal, o rewarm vai para a pessoa errada, mas o agente lendo a conversa provavelmente retorna `skip` com razão. Não é perfeito mas é contido.

- **[Mensagem de rewarm fica indistinguível de mensagem do operador no histórico]** → Mitigação: usar `sent_by='rewarm_agent'` ou `'rewarm_reviewed'` para distinguir. Útil tanto pra auditoria quanto pra a análise de qualidade.

## Migration Plan

Não há migração de dados. Deploy é aditivo:
1. Merge do código (service, rota, config flag, frontend).
2. Deploy com `REWARM_AUTO_SEND=false`.
3. Operador usa o botão nos primeiros dias, revisa mensagens, envia.
4. Quando confiança estiver alta, setar `REWARM_AUTO_SEND=true` e agendar cron diário (fora de escopo deste change).

**Rollback:** desligar a flag e/ou remover o botão da UI. O código pode ficar dormente sem impacto em outras funcionalidades.

## Open Questions

- Horário ótimo de execução quando virar cron (manhã cedo? meio da manhã?). Fora de escopo — resolver quando for agendar.
- Valor de `sent_by` para mensagens enviadas pelo rewarm. Proposta: `rewarm_agent` (automático) e `rewarm_reviewed` (passou pela tela). Alinhar com Caio no momento da implementação.
