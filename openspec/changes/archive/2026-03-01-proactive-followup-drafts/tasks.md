## 1. Backend: Draft engine

- [x] 1.1 Adicionar parâmetro `proactive: bool = False` em `generate_drafts()` e `_build_prompt_parts()`
- [x] 1.2 Condicionar a instrução final do prompt: usar instrução de continuação quando `proactive=True`
- [x] 1.3 Ajustar `regenerate_draft()` para propagar o flag `proactive` na regeneração

## 2. Backend: Endpoint de sugestão

- [x] 2.1 Criar endpoint `POST /conversations/{id}/suggest` em `app/routes/messages.py`
- [x] 2.2 Validar que a última mensagem é outbound, retornar 409 se for inbound
- [x] 2.3 Buscar ID da última mensagem e disparar `generate_drafts(conversation_id, last_msg_id, proactive=True)`

## 3. Frontend: Botão "Sugerir resposta"

- [x] 3.1 Adicionar markup e CSS do botão em `index.html` (dentro de `#compose`, acima do `#draft-cards-container`)
- [x] 3.2 Em `openConversation()`, detectar se última mensagem é outbound e não há drafts pendentes -> mostrar botão
- [x] 3.3 Implementar `requestSuggestion()`: chamar endpoint, mostrar loading, esconder botão quando `drafts_ready` chegar via WebSocket
- [x] 3.4 Esconder botão quando drafts reativos chegam (evento `drafts_ready` do WebSocket)

## 4. Frontend: Ajuste no envio

- [x] 4.1 No fluxo de envio, quando o draft veio de geração proativa, usar a última mensagem outbound como `customer_message` para o edit_pair (isso acontece no backend via `trigger_message_id`)

## 5. Testes

- [x] 5.1 Teste do endpoint `/suggest` com última mensagem outbound (happy path)
- [x] 5.2 Teste do endpoint `/suggest` com última mensagem inbound (deve retornar 409)
- [x] 5.3 Teste do draft engine com `proactive=True` verificando que a instrução final do prompt muda
