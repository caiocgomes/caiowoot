## Context

Scheduled sends é uma feature com 3 camadas: rotas CRUD (create/list/cancel), background worker (`_process_due_sends`), e auto-cancel via webhook. O conftest.py já patcha `app.routes.scheduled.get_db` e `app.services.scheduler.get_db`, então a infraestrutura de teste está pronta. Os testes existentes em `test_webhook.py` já cobrem o fluxo de mensagem inbound mas não verificam o cancelamento de agendamentos.

## Goals / Non-Goals

**Goals:**
- Cobertura de todos os caminhos das rotas CRUD (happy path + erros 404/422/409)
- Cobertura do `_process_due_sends()` incluindo envio, marcação como sent, e retry em falha
- Teste de integração do auto-cancel no webhook quando cliente responde
- Usar patterns do conftest.py existente (fixtures `db`, `client`, `mock_evolution_api`)

**Non-Goals:**
- Testar `scheduler_loop()` (é só polling com sleep, sem lógica)
- Testar WebSocket broadcast real (já mockado no conftest)
- Mudar código de produção
- Testar o `send_executor.py` em si (já tem 90% de cobertura)

## Decisions

**1. Teste direto de `_process_due_sends()` vs teste via endpoint**
Testar `_process_due_sends()` diretamente chamando a função, não via loop. O loop é trivial (while True + sleep). A função é onde a lógica vive. Para simular "mensagem está due", inserimos no banco com `send_at` no passado.

**2. Mock de `execute_send` no scheduler**
O scheduler chama `execute_send()` que faz chamada à Evolution API. Nos testes do scheduler, mockamos `execute_send` para isolar a lógica de polling/status management. Os testes de `execute_send` já existem em `test_message_sender.py`.

**3. Auto-cancel como extensão de test_webhook.py**
O auto-cancel é comportamento do webhook handler, não do scheduler. Então o teste fica em `test_webhook.py` junto dos outros testes de webhook, não em arquivo separado.

## Risks / Trade-offs

- [Acoplamento temporal] O `_process_due_sends` usa `datetime('now')` do SQLite. Nos testes, inserimos com `send_at` no passado para garantir que são "due". Funciona porque SQLite `:memory:` tem o mesmo relógio. → Sem mitigação necessária, padrão funciona.
- [`total_changes` no cancel] A rota de cancel usa `db.total_changes` para detectar se o update pegou alguma row, que é um counter global do SQLite, não por statement. Em produção com conexões concorrentes pode dar falso positivo. → Fora do escopo (não é bug de teste), mas o teste deve exercitar o cenário.
