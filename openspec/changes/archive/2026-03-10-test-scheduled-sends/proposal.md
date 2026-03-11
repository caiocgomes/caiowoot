## Why

A feature de scheduled sends (scheduler.py 23%, routes/scheduled.py 35%) é a pior cobertura do codebase e lida com envio automático de mensagens para clientes. Sem testes, qualquer mudança nessa área pode causar mensagens duplicadas, mensagens que nunca saem, ou mensagens enviadas fora de contexto quando o cliente já respondeu. O operador depende dessa feature para follow-ups e não tem como saber se quebrou até o cliente reclamar.

## What Changes

- Testes para as 3 rotas CRUD de scheduled sends (POST create, GET list, DELETE cancel) cobrindo happy paths e erros (404, 422, 409)
- Testes para `_process_due_sends()` cobrindo envio normal, marcação como sent, e retry em caso de falha
- Teste de integração no webhook para auto-cancel de agendamentos pendentes quando cliente responde
- Nenhuma mudança em código de produção

## Capabilities

### New Capabilities

- `test-scheduled-sends`: Cobertura de testes para scheduled sends (rotas CRUD, background worker, auto-cancel via webhook)

### Modified Capabilities

## Impact

- `tests/test_scheduled_sends.py` (novo) - testes das rotas e do scheduler
- `tests/test_webhook.py` (modificado) - teste de auto-cancel por mensagem inbound
- Sem mudanças em código de produção, banco, ou APIs
