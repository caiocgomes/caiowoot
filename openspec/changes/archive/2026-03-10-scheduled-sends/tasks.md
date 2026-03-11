## 1. Database e Migration

- [x] 1.1 Adicionar migration para criar tabela `scheduled_sends` com índice em `(status, send_at)` em `database.py:MIGRATIONS`
- [x] 1.2 Verificar que migration roda corretamente no startup

## 2. Extração da Lógica de Envio

- [x] 2.1 Extrair lógica core de envio de `routes/messages.py` para função `execute_send()` em `services/send_executor.py` (Evolution API call + insert messages + edit_pair + WebSocket broadcast)
- [x] 2.2 Refatorar endpoint `POST /conversations/{id}/send` para usar `execute_send()`
- [x] 2.3 Testes: garantir que o send existente continua funcionando identicamente após refactor

## 3. Endpoints de Agendamento

- [x] 3.1 Criar endpoint `POST /conversations/{id}/schedule` (content, send_at, draft metadata opcional) que insere em `scheduled_sends` e broadcast WebSocket `scheduled_send_created`
- [x] 3.2 Criar endpoint `GET /conversations/{id}/scheduled` que retorna envios pendentes ordenados por `send_at`
- [x] 3.3 Criar endpoint `DELETE /scheduled-sends/{id}` para cancelamento manual (status → cancelled, reason → operator_cancelled, broadcast WebSocket)
- [ ] 3.4 Testes dos três endpoints

## 4. Background Worker (Polling Loop)

- [x] 4.1 Criar `services/scheduler.py` com loop asyncio que a cada 30s busca envios pendentes com `send_at <= now()`, transiciona atomicamente para `sending`, e chama `execute_send()`
- [x] 4.2 Tratar falha da Evolution API: reverter status para `pending` para retry no próximo ciclo
- [x] 4.3 Registrar o loop como startup event do FastAPI (`app.on_event("startup")` ou lifespan)
- [ ] 4.4 Testes do scheduler com mock de tempo e Evolution API

## 5. Auto-cancelamento no Webhook

- [x] 5.1 Modificar handler do webhook em `routes/webhook.py`: após inserir mensagem inbound, executar `UPDATE scheduled_sends SET status='cancelled', cancelled_reason='client_replied', cancelled_by_message_id=? WHERE conversation_id=? AND status='pending'`
- [x] 5.2 Se rows afetadas > 0, broadcast WebSocket `scheduled_send_cancelled` para cada envio cancelado
- [ ] 5.3 Testes: webhook com e sem envios agendados pendentes

## 6. Frontend

- [x] 6.1 Adicionar botão "Agendar" ao lado do "Enviar" com dropdown de opções (30min, 1h, 2h, Amanhã 9h, Amanhã 14h, Custom)
- [x] 6.2 Para opção "Custom", implementar input de date/time
- [x] 6.3 Ao agendar, chamar `POST /schedule` e resetar UI como no send normal
- [x] 6.4 Exibir pill/banner de envio agendado na conversa (horário, preview do texto, botão cancelar)
- [x] 6.5 Ao abrir conversa, buscar `GET /scheduled` e renderizar pills de agendamentos pendentes
- [x] 6.6 Adicionar ícone de relógio na lista de conversas para conversas com envios pendentes
- [x] 6.7 Tratar eventos WebSocket `scheduled_send_created`, `scheduled_send_cancelled`, `scheduled_send_completed` para atualizar UI em real-time
