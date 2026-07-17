## Why

Quando um lead manda a primeira mensagem, ele está quente. Se o operador demora 5-10 minutos para responder, o lead esfria. Ao mesmo tempo, os primeiros minutos de toda conversa são repetitivos: saber o nome, qual curso interessa, se já trabalha na área, qual o objetivo. Esse qualifying pode ser feito por um robô transparente que mantém o lead engajado enquanto coleta informações úteis para o operador.

O robô nunca finge ser humano. Ele se apresenta como assistente, faz 3-4 perguntas de qualificação, e quando tem o que precisa, passa a conversa para o operador humano com um resumo pronto. A conversa nunca volta para o robô.

## What Changes

### Database
- Adicionar campo `is_qualified` (boolean, default False) na tabela `conversations`
- Novas conversas começam com `is_qualified = False`

### Backend: Auto-resposta no qualifying
- Quando uma mensagem inbound chega e `is_qualified = False`: robô gera resposta automaticamente via Claude e envia pelo Evolution API, sem intervenção do operador
- O prompt do robô é restrito: qualifica (curso, experiência, objetivo, dúvida), NÃO vende, NÃO dá preço, NÃO faz promessa
- O robô usa o histórico da conversa para decidir: continuar qualificando ou fazer handoff
- Quando o robô decide que tem informação suficiente: envia mensagem de handoff ("vou passar pro Caio/Bia"), seta `is_qualified = True`, gera situation summary

### Backend: Assumir conversa manualmente
- Novo endpoint `POST /conversations/{id}/assume` que seta `is_qualified = True`
- Quando operador assume, robô para imediatamente (próxima mensagem inbound gera drafts normais)

### Frontend: Estado visual
- Conversas com `is_qualified = False` aparecem com cor diferente (amarela/laranja) na sidebar
- Ao abrir conversa não qualificada: área de composição bloqueada, mostra botão "Assumir conversa" no lugar do "Enviar"
- Clicar "Assumir" chama o endpoint e desbloqueia a conversa
- Conversas qualificadas (True) ficam verdes / comportamento normal

### Webhook: Roteamento
- No webhook de mensagem inbound, checar `is_qualified`:
  - Se False: disparar auto-resposta do robô (não gerar drafts)
  - Se True: fluxo normal (gerar drafts para operador)

## Capabilities

### New Capabilities
- `auto-qualifying`: Robô de qualificação automática para primeiras conversas
- `conversation-assume`: Mecanismo de assumir conversa manualmente pelo operador

### Modified Capabilities
- `webhook-receiver`: Roteamento condicional baseado em is_qualified
- `draft-engine`: Não gerar drafts para conversas em qualifying

## Impact

- `app/database.py` — novo campo is_qualified na tabela conversations + migration
- `app/routes/webhook.py` — lógica condicional de roteamento
- `app/routes/conversations.py` — endpoint /assume, retornar is_qualified no list e detail
- `app/services/` — novo serviço de auto-qualifying (prompt + envio + handoff detection)
- `app/static/js/` — estado visual da conversa, bloqueio de composição, botão assumir
- `app/static/css/` — cor diferente para conversas em qualifying
