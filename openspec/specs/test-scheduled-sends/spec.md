## ADDED Requirements

### Requirement: Testes das rotas CRUD de scheduled sends
O sistema de testes SHALL cobrir create, list e cancel de scheduled sends via HTTP endpoints, validando happy paths e todos os caminhos de erro.

#### Scenario: Criar agendamento com sucesso
- **WHEN** POST `/conversations/{id}/schedule` com content, send_at válido e conversa existente
- **THEN** retorna 200 com scheduled_send contendo id, content, send_at, status "pending"

#### Scenario: Criar agendamento para conversa inexistente
- **WHEN** POST `/conversations/99999/schedule` com conversa que não existe
- **THEN** retorna 404

#### Scenario: Criar agendamento com send_at inválido
- **WHEN** POST `/conversations/{id}/schedule` com send_at que não é ISO 8601 válido
- **THEN** retorna 422

#### Scenario: Listar agendamentos pendentes
- **WHEN** GET `/conversations/{id}/scheduled` com conversa que tem agendamentos pending
- **THEN** retorna lista de agendamentos pendentes ordenados por send_at

#### Scenario: Listar agendamentos de conversa inexistente
- **WHEN** GET `/conversations/99999/scheduled`
- **THEN** retorna 404

#### Scenario: Cancelar agendamento pendente
- **WHEN** DELETE `/scheduled-sends/{id}` com agendamento em status pending
- **THEN** retorna 200, status muda para cancelled com reason "operator_cancelled"

#### Scenario: Cancelar agendamento inexistente
- **WHEN** DELETE `/scheduled-sends/99999`
- **THEN** retorna 404

#### Scenario: Cancelar agendamento já enviado
- **WHEN** DELETE `/scheduled-sends/{id}` com agendamento em status sent
- **THEN** retorna 409

### Requirement: Testes do background worker _process_due_sends
O sistema de testes SHALL cobrir o processamento de mensagens agendadas que atingiram o horário de envio, incluindo sucesso, marcação de status e retry em falha.

#### Scenario: Processar envio due com sucesso
- **WHEN** existe scheduled_send com status pending e send_at no passado
- **AND** `_process_due_sends()` é chamado
- **THEN** `execute_send` é chamado com conversation_id, content e created_by corretos
- **AND** status muda para "sent" com sent_at preenchido

#### Scenario: Ignorar envios não-due
- **WHEN** existe scheduled_send com status pending e send_at no futuro
- **AND** `_process_due_sends()` é chamado
- **THEN** `execute_send` não é chamado
- **AND** status permanece "pending"

#### Scenario: Retry em caso de falha no envio
- **WHEN** existe scheduled_send due e `execute_send` levanta exceção
- **AND** `_process_due_sends()` é chamado
- **THEN** status reverte para "pending" para retry no próximo ciclo

### Requirement: Teste de auto-cancel via webhook
O sistema de testes SHALL verificar que mensagens inbound cancelam agendamentos pendentes da mesma conversa.

#### Scenario: Mensagem inbound cancela agendamentos pendentes
- **WHEN** conversa tem scheduled_sends pendentes
- **AND** webhook recebe mensagem inbound do cliente nessa conversa
- **THEN** todos os scheduled_sends pendentes são cancelados com reason "client_replied"
- **AND** scheduled_sends já enviados não são afetados
