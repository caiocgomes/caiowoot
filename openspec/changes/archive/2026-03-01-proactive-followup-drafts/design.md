## Context

O fluxo atual de drafts é reativo: webhook recebe mensagem inbound -> `generate_drafts(conversation_id, trigger_message_id)` onde `trigger_message_id` é sempre uma mensagem inbound do cliente. O prompt termina com "Gere o draft de resposta para a última mensagem do cliente."

O operador precisa retomar conversas onde ele foi o último a falar. Nesses casos, não existe mensagem inbound pendente e nenhum draft é gerado.

Constraint importante: `drafts.trigger_message_id` é `NOT NULL` no schema. `edit_pairs.customer_message` também é `NOT NULL`.

## Goals / Non-Goals

**Goals:**
- Operador pode solicitar drafts de continuação quando a última mensagem é outbound
- Reutilizar o máximo do fluxo existente (draft engine, 3 variações, WebSocket, etc.)
- Drafts proativos passam pelo mesmo ciclo de exibição, seleção e envio

**Non-Goals:**
- Geração automática (sem trigger do operador)
- Mudar o fluxo reativo existente (quando chega mensagem do cliente)
- Alterar o schema de `edit_pairs` para suportar `customer_message` NULL

## Decisions

**Decisão 1: `trigger_message_id` aponta para a última mensagem (outbound)**

Em vez de tornar `trigger_message_id` nullable, apontamos para a última mensagem da conversa, que nesse caso é outbound. Isso mantém a constraint NOT NULL e é semanticamente correto: o draft é um followup a essa mensagem.

O draft engine recebe um parâmetro `proactive=True` para saber que deve ajustar a instrução final do prompt.

**Decisão 2: Instrução final do prompt condicional**

Quando `proactive=True`, a instrução final muda de:
> "Gere o draft de resposta para a última mensagem do cliente."

Para:
> "A última mensagem da conversa foi enviada pelo Caio. Gere uma mensagem de continuação natural, retomando o contexto da conversa."

O resto do prompt (knowledge base, few-shot, regras, temporal context) permanece igual. O temporal context já calcula tempo desde última mensagem inbound, o que dá ao modelo noção de quanto tempo passou.

**Decisão 3: Novo endpoint `POST /conversations/{id}/suggest`**

Endpoint dedicado, separado do webhook e do regenerate. Verifica que a última mensagem é outbound, busca o ID dela, e chama `generate_drafts(conversation_id, last_msg_id, proactive=True)`.

Alternativa descartada: reutilizar endpoint de regenerate. A semântica é diferente (não há draft anterior para regenerar).

**Decisão 4: Botão "Sugerir resposta" no frontend**

Aparece no lugar dos draft cards quando: (1) não há drafts pendentes e (2) a última mensagem carregada é outbound. Ao clicar, chama `POST /conversations/{id}/suggest` e exibe loading. Quando os drafts chegam via WebSocket (evento `drafts_ready`), são exibidos normalmente.

**Decisão 5: `edit_pairs.customer_message` para drafts proativos**

Quando o operador envia uma mensagem baseada num draft proativo, o `customer_message` no edit_pair será a última mensagem outbound (a que motivou o followup). Isso mantém o NOT NULL e dá contexto para o sistema de aprendizado entender a situação.

## Risks / Trade-offs

- [Custo API] -> Mitigado pela opção B (botão explícito). Só gera quando o operador pede.
- [Few-shot retrieval menos preciso] -> O situation summary de um followup é diferente de uma resposta a pergunta. Os exemplos recuperados podem ser menos relevantes. Aceitável como v1, o sistema aprende com o tempo.
- [Temporal context mostra tempo desde última inbound] -> Para followups, isso pode ser confuso. Mas o prompt tem o histórico completo, então o modelo consegue inferir o gap correto.
