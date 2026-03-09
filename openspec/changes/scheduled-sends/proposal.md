## Why

O operador frequentemente promete ao cliente "te mando mensagem em uma hora" ou "amanhã te retomo". Hoje não existe mecanismo para agendar esse envio, dependendo da memória do operador. Isso causa follow-ups perdidos e leads que esfriam.

## What Changes

- Novo mecanismo de envio agendado: operador compõe a mensagem, define horário, e o sistema envia automaticamente
- Auto-cancelamento: se o cliente mandar mensagem antes do horário agendado, o envio é cancelado automaticamente (mensagem pré-composta perdeu contexto)
- Background polling loop que verifica envios pendentes a cada 30 segundos
- UI com botão "Agendar" ao lado do "Enviar", com opções rápidas de tempo (30min, 1h, 2h, amanhã 9h, amanhã 14h, custom)
- Indicador visual de envio agendado na conversa e na lista de conversas

## Capabilities

### New Capabilities
- `scheduled-sends`: Agendamento de envio de mensagens de texto com auto-cancelamento por resposta do cliente. Inclui persistência em SQLite, background worker, endpoints de CRUD, e integração com o learning loop.

### Modified Capabilities
- `webhook-receiver`: Webhook de mensagem inbound precisa cancelar envios agendados pendentes da conversa
- `message-sender`: Lógica de envio precisa ser extraída para função compartilhada (usada pelo endpoint direto e pelo background worker)

## Impact

- **Database**: nova tabela `scheduled_sends`, nova migration
- **Backend**: novo módulo `app/services/scheduler.py` (polling loop), novos endpoints em routes, modificação do webhook handler e extração de lógica do send endpoint
- **Frontend**: botão "Agendar" com time picker, pill de envio agendado na conversa, ícone de relógio na lista de conversas
- **WebSocket**: novos eventos `scheduled_send_created`, `scheduled_send_cancelled`, `scheduled_send_completed`
