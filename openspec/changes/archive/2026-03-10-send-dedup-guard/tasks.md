## 1. Backend

- [x] 1.1 Adicionar função `check_duplicate_send(db, conversation_id, content)` em `send_executor.py` que consulta última mensagem outbound e retorna True se duplicata dentro de 5s
- [x] 1.2 Chamar guard em `execute_send()` antes de enviar via Evolution API, levantando DuplicateSendError se duplicata
- [x] 1.3 Adicionar guard também no path de envio com arquivo em `routes/messages.py` (que não usa execute_send)
- [ ] 1.4 Testes: duplicata bloqueada, mensagem diferente permitida, mesma mensagem após 5s permitida, primeira mensagem permitida
