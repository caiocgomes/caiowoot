## Why

Quando a geração automática de drafts falha (erro na API Anthropic, timeout, falha no prompt building), o operador fica sem nenhuma ação disponível na UI. A barra de instrução e o botão regenerar só aparecem depois que os drafts existem, criando um beco sem saída silencioso. O operador precisa de um mecanismo manual pra disparar geração a qualquer momento, sem depender do fluxo automático ter funcionado.

## What Changes

- A barra de instrução com o botão "Regenerar" passa a ser **sempre visível** na área de compose quando uma conversa está aberta, independente de existirem drafts pendentes
- O botão "Regenerar" funciona mesmo sem drafts prévios: identifica o `trigger_message_id` da última mensagem inbound da conversa e dispara a geração
- O botão "Sugerir resposta" (proactive-followup) é removido. A barra de instrução + regenerar cobre esse caso
- Quando não há drafts e não há `currentDrafts`, o JS busca o trigger_message_id direto das mensagens carregadas

## Capabilities

### New Capabilities
_Nenhuma_

### Modified Capabilities
- `draft-variations`: A barra de instrução e o botão regenerar passam a ser sempre visíveis, e o regenerate funciona sem drafts prévios
- `proactive-followup`: Removido. A barra de instrução com regenerar substitui o botão "Sugerir resposta"

## Impact

- `app/static/app.js`: Lógica de visibilidade da instruction-bar e do regenerate. Fallback para trigger_message_id sem currentDrafts
- `app/static/index.html`: Remover suggest-btn. Garantir instruction-bar visível por padrão
- `app/routes/messages.py`: Endpoint regenerate precisa aceitar chamadas sem draft_group_id existente (já funciona, mas validar)
