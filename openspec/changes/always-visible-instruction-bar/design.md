## Context

A barra de instrução e o botão regenerar só aparecem no frontend quando `showDrafts()` é chamada. Se `generate_drafts()` falha silenciosamente (API Anthropic fora, timeout, erro no prompt building), o operador vê a mensagem do cliente mas não tem nenhuma ação disponível pra disparar a geração de drafts manualmente.

O botão "Sugerir resposta" cobre o caso outbound mas não o caso inbound sem drafts.

## Goals / Non-Goals

**Goals:**
- Instruction bar + botão regenerar sempre visíveis quando uma conversa está aberta
- Regenerar funciona mesmo sem drafts prévios (identifica trigger_message_id da conversa)
- Remover o botão "Sugerir resposta" (a barra de instrução substitui)

**Non-Goals:**
- Adicionar broadcast de erro do backend (pode ser feito depois)
- Mudar o fluxo automático de geração de drafts
- Timeout/retry automático no frontend

## Decisions

### 1. Instruction bar sempre visível via CSS/HTML

Hoje a instruction-bar tem `display: none` no CSS e é mostrada via JS em `showDrafts()`. A mudança é inverter: a barra começa visível por padrão quando o compose está ativo. O `openConversation()` não precisa mais esconder ela.

Alternativa descartada: mostrar via JS no `openConversation()`. Mais frágil, depende de lembrar de setar em todos os code paths.

### 2. Fallback para trigger_message_id sem currentDrafts

Hoje `regenerateAll()` pega `currentDrafts[0].trigger_message_id`. Sem drafts, esse valor é undefined. A solução é manter uma variável `lastInboundMessageId` atualizada em `openConversation()` e `handleWSEvent(new_message)`. O `regenerateAll()` usa `currentDrafts[0]?.trigger_message_id || lastInboundMessageId`.

### 3. Regenerar sem drafts chama /regenerate com draft_index: null

O endpoint `/regenerate` já lida com o caso de não encontrar drafts existentes (cria novo `draft_group_id`). Não precisa de mudança no backend.

### 4. Remover suggest-btn e requestSuggestion()

O botão "Sugerir resposta" e a função `requestSuggestion()` são removidos. O operador usa a mesma barra de instrução + regenerar pra ambos os casos (inbound sem draft e outbound querendo follow-up). A flag `proactive` no regenerate não é necessária pra esse fluxo; o operador digita a instrução que quiser (ex: "gera um follow-up") e clica regenerar.

O endpoint `POST /suggest` e a função `suggest_followup()` no backend permanecem intactos (podem ser úteis no futuro ou via API), mas o frontend deixa de usá-los.

## Risks / Trade-offs

- **Botão regenerar sem contexto visual**: sem drafts na tela, o operador pode não entender que o botão vai gerar sugestões. Mitigação: o placeholder do input já diz "Instrução para a IA". O fluxo é intuitivo o suficiente.
- **Proactive follow-up menos explícito**: antes tinha um botão dedicado "Sugerir resposta". Agora o operador precisa saber que pode usar o regenerar pra isso. Mitigação: o operador principal é o próprio Caio, que já sabe do fluxo.
