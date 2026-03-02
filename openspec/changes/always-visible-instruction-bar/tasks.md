## 1. Frontend: instruction bar sempre visível

- [x] 1.1 Em `index.html`, remover `display: none` do CSS de `#instruction-bar` (linha 66). A barra fica visível por padrão quando o compose está ativo
- [x] 1.2 Em `app.js` `openConversation()`, remover a linha que esconde a instruction-bar (`document.getElementById("instruction-bar").style.display = "none"`) e remover a linha que mostra ela em `showDrafts()` (`document.getElementById("instruction-bar").style.display = "block"`)

## 2. Frontend: remover suggest-btn

- [x] 2.1 Em `index.html`, remover o elemento `<button id="suggest-btn">`
- [x] 2.2 Em `app.js`, remover a função `requestSuggestion()` e todas as referências a `suggest-btn` (em `openConversation()`, `showDrafts()`, `handleWSEvent`)

## 3. Frontend: regenerar sem drafts prévios

- [x] 3.1 Em `app.js`, adicionar variável `let lastTriggerMessageId = null` no topo
- [x] 3.2 Em `openConversation()`, após carregar mensagens, setar `lastTriggerMessageId` com o ID da última mensagem inbound (ou última mensagem se nenhuma é inbound)
- [x] 3.3 Em `handleWSEvent(new_message)`, se a mensagem é inbound e é da conversa atual, atualizar `lastTriggerMessageId`
- [x] 3.4 Em `regenerateAll()`, trocar `currentDrafts[0].trigger_message_id` por `currentDrafts[0]?.trigger_message_id || lastTriggerMessageId`. Adicionar guard: se nenhum trigger_message_id disponível, retornar sem ação
- [x] 3.5 Em `regenerateDraft(index)`, aplicar o mesmo fallback para trigger_message_id

## 4. Verificação

- [x] 4.1 Testar: abrir conversa com drafts pendentes, verificar que instruction bar e draft cards aparecem
- [ ] 4.2 Testar: abrir conversa com inbound sem drafts, verificar que instruction bar aparece e botão regenerar funciona (teste manual no servidor)
- [ ] 4.3 Testar: receber nova mensagem via WS, simular falha de drafts, clicar regenerar na barra de instrução (teste manual no servidor)
