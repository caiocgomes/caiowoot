## Why

Sem horário visível nas mensagens, o operador perde contexto temporal da conversa: não sabe quanto tempo o cliente esperou por resposta, nem identifica gaps entre interações. Isso dificulta decisões de urgência e tom.

## What Changes

- Exibir horário (HH:MM) abaixo de cada mensagem na interface de chat
- Agrupar visualmente mensagens do mesmo dia com separador de data quando houver mudança de dia
- Reutilizar `formatTime()` já existente ou criar variante para formato curto (só hora)

## Capabilities

### New Capabilities

- `message-timestamps`: Exibição de horários nas mensagens do chat e separadores de data entre dias diferentes

### Modified Capabilities

_Nenhuma. O backend já retorna `created_at` em todas as mensagens. Change puramente de frontend._

## Impact

- `app/static/app.js` — modificar `appendMessage()` para renderizar timestamp
- `app/static/index.html` — CSS para estilização do timestamp e separador de data
- Nenhuma mudança de API, banco ou backend
