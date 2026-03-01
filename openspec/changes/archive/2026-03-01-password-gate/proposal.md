## Why

O CaioWoot precisa ser exposto na internet para uso remoto. Sem nenhuma proteção, qualquer pessoa com a URL teria acesso completo: ler conversas de clientes, enviar mensagens no WhatsApp, manipular regras de aprendizado. Uma senha compartilhada simples resolve o problema sem a complexidade de um sistema de usuários.

## What Changes

- Novo middleware de autenticação que intercepta todas as rotas (exceto webhook e login)
- Tela de login no frontend pedindo senha
- Sessão via cookie assinado com expiração configurável
- Rate limiting no endpoint de login contra brute force
- Validação de auth no WebSocket antes de aceitar conexão
- Nova dependência: `itsdangerous` para assinatura de cookies

## Capabilities

### New Capabilities
- `password-gate`: Autenticação por senha compartilhada, sessão via cookie, rate limiting, proteção de WebSocket

### Modified Capabilities
- `webhook-receiver`: Webhook precisa de bypass explícito na autenticação (Evolution API precisa postar sem senha)
- `inbox-ui`: Frontend precisa de tela de login e lógica de redirecionamento quando não autenticado

## Impact

- **Backend**: Novo middleware em `app/main.py`, novo endpoint `POST /login`, novo endpoint `POST /logout`, nova dependência `itsdangerous`
- **Frontend**: Nova tela de login em `index.html`/`app.js`, tratamento de 401 nas chamadas de API
- **WebSocket**: Validação de cookie no handshake em `app/websocket_manager.py`
- **Deploy**: Nova env var `APP_PASSWORD` obrigatória, `SESSION_MAX_AGE` opcional
- **Webhook**: Sem impacto funcional, apenas bypass explícito no middleware
