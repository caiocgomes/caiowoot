## Context

O CaioWoot é um app FastAPI que serve uma SPA (vanilla HTML/JS) via StaticFiles. Atualmente roda em rede local sem autenticação. Para expor na internet, precisa de uma camada de proteção simples: senha compartilhada.

A stack atual: FastAPI + aiosqlite + WebSocket. Frontend é vanilla JS sem framework. Não há sistema de usuários e não é objetivo ter um agora.

## Goals / Non-Goals

**Goals:**
- Impedir acesso não autorizado a todas as rotas (HTTP e WebSocket)
- Manter webhook acessível para Evolution API
- Rate limiting contra brute force
- Sessão segura via cookie assinado
- Experiência mínima de login no frontend
- Funcionar sem auth quando `APP_PASSWORD` não está definido (dev local)

**Non-Goals:**
- Múltiplos usuários ou roles
- OAuth, JWT, ou qualquer sistema de identidade
- HTTPS (responsabilidade da infra, não do código)
- Persistência de sessão (cookie assinado é stateless)
- UI elaborada de login

## Decisions

### 1. Middleware Starlette vs. FastAPI Depends

**Decisão:** Middleware Starlette (`BaseHTTPMiddleware`).

**Alternativas:**
- `Depends()` em cada rota: granular mas requer tocar todas as rotas existentes, fácil de esquecer uma
- Middleware: intercepta tudo, allowlist explícita para exceções

Middleware é mais seguro por default: qualquer rota nova é automaticamente protegida. A allowlist é pequena e estável (`/webhook`, `/login`, `/login.html`).

### 2. Sessão: itsdangerous vs. JWT vs. session store

**Decisão:** `itsdangerous.URLSafeTimedSerializer` para assinar um cookie.

**Alternativas:**
- JWT: overhead desnecessário para single-user, precisa de lib extra mais pesada
- Server-side session (Redis/DB): complexidade sem benefício para single-user
- `itsdangerous`: leve, já battle-tested, assinatura + expiração built-in, zero state no server

O cookie contém apenas um payload assinado (ex: `{"authenticated": true, "ts": ...}`). A chave de assinatura é a própria `APP_PASSWORD` (se alguém tem a senha, já pode fazer login de qualquer forma).

### 3. Rate limiting: in-memory dict vs. biblioteca

**Decisão:** Dict simples `{ip: [timestamps]}` com limpeza lazy.

**Alternativas:**
- `slowapi` / `limits`: dependência extra para um único endpoint
- Redis-backed: overkill

Volume esperado é baixíssimo. Um dict com janela deslizante de 1 minuto resolve. A limpeza de IPs antigos acontece no próprio check (remove timestamps > 60s).

### 4. Login page: rota FastAPI vs. arquivo estático

**Decisão:** Arquivo estático `login.html` servido pelo StaticFiles.

Motivo: sem lógica server-side na página de login. O form faz `fetch` para `POST /login` e redireciona via JS. Simples de manter junto com o index.html existente.

### 5. WebSocket auth: cookie no handshake

O browser envia cookies automaticamente no handshake WebSocket. O endpoint `/ws` valida o cookie antes de chamar `manager.connect()`. Se inválido, fecha com code 4401.

### 6. Fallback quando APP_PASSWORD não definido

Se `APP_PASSWORD` não está configurado (string vazia ou não definida), o middleware não bloqueia nada. Permite desenvolvimento local sem fricção. Nenhum campo obrigatório no Settings (default `""`).

## Risks / Trade-offs

**[Senha em plaintext na env var]** → Aceitável: todas as outras secrets (Anthropic, Evolution) já estão no mesmo .env. Se o .env vaza, a senha de login é o menor problema.

**[Rate limit in-memory]** → Reseta no restart do processo. Aceitável para o volume (10-20 conversas/dia). Se fosse multi-instance, precisaria de Redis.

**[Cookie secret = APP_PASSWORD]** → Se alguém descobre a senha, pode tanto fazer login quanto forjar cookies. Sem impacto prático: ambos dão o mesmo acesso.

**[Sem CSRF token]** → Mitigado por `SameSite=Strict` no cookie. Nenhum form externo consegue enviar request com o cookie.

## Open Questions

Nenhuma. Escopo é pequeno e decisões estão claras.
