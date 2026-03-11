## 1. Testes das rotas CRUD (tests/test_scheduled_sends.py)

- [x] 1.1 Criar arquivo test_scheduled_sends.py com helpers para inserir conversa e scheduled_send no banco de teste
- [x] 1.2 Teste: criar agendamento com sucesso (POST, verifica response e registro no banco)
- [x] 1.3 Teste: criar agendamento para conversa inexistente (404)
- [x] 1.4 Teste: criar agendamento com send_at inválido (422)
- [x] 1.5 Teste: listar agendamentos pendentes (GET, verifica ordenação por send_at)
- [x] 1.6 Teste: listar agendamentos de conversa inexistente (404)
- [x] 1.7 Teste: cancelar agendamento pendente (DELETE, verifica status cancelled e reason)
- [x] 1.8 Teste: cancelar agendamento inexistente (404)
- [x] 1.9 Teste: cancelar agendamento já enviado (409)

## 2. Testes do background worker (tests/test_scheduled_sends.py)

- [x] 2.1 Teste: _process_due_sends processa envio due com sucesso (mock execute_send, verifica status sent)
- [x] 2.2 Teste: _process_due_sends ignora envios com send_at no futuro
- [x] 2.3 Teste: _process_due_sends reverte para pending quando execute_send falha

## 3. Teste de auto-cancel no webhook (tests/test_webhook.py)

- [x] 3.1 Teste: mensagem inbound cancela scheduled_sends pendentes da conversa com reason client_replied
