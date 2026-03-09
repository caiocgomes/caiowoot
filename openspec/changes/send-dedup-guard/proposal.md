## Why

Duplo-clique no botão de enviar ou race conditions no frontend podem causar envio duplicado da mesma mensagem para o mesmo contato. Não existe guard contra isso hoje.

## What Changes

- Guard no backend que rejeita envio de mensagem idêntica para a mesma conversa dentro de janela de 5 segundos
- Retorna erro claro para o frontend quando detecta duplicata

## Capabilities

### New Capabilities

### Modified Capabilities
- `message-sender`: Adicionar guard de deduplicação antes do envio via Evolution API

## Impact

- **Backend**: modificação no fluxo de envio (send_executor ou endpoint) para checar última mensagem enviada
- Sem mudanças no banco (usa query na tabela messages existente)
- Sem mudanças no frontend (guard é server-side, erro é tratado pelo handler existente)
