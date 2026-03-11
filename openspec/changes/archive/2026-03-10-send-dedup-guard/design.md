## Context

O envio de mensagens passa pelo `execute_send()` (extraído recentemente para `send_executor.py`) e pelo endpoint direto em `routes/messages.py` (para envios com arquivo). Ambos chamam a Evolution API e inserem na tabela `messages`.

## Goals / Non-Goals

**Goals:**
- Prevenir envio duplicado da mesma mensagem para a mesma conversa em janela de 5 segundos

**Non-Goals:**
- Deduplicação no frontend (desabilitar botão, etc.)
- Deduplicação de mensagens diferentes
- Deduplicação de mensagens inbound (já existe via `evolution_message_id` UNIQUE)

## Decisions

### Guard no execute_send() e no endpoint de envio com arquivo
Antes de chamar a Evolution API, consultar a última mensagem outbound da conversa. Se `content` for idêntico e `created_at` estiver dentro de 5 segundos, rejeitar com HTTP 409 Conflict.

Query: `SELECT content, created_at FROM messages WHERE conversation_id = ? AND direction = 'outbound' ORDER BY created_at DESC LIMIT 1`

Comparação simples de string (case-sensitive). 5 segundos é curto o suficiente para pegar duplo-clique mas não bloquear envios legítimos de mensagens repetidas (ex: reenviar link).

### Também aplicar no scheduled send worker
O scheduler em `scheduler.py` usa `execute_send()`, então o guard se aplica automaticamente. Se um envio agendado for duplicata de algo enviado manualmente segundos antes, será rejeitado (status volta a pending, mas na prática isso é improvável).

## Risks / Trade-offs

- **[Falso positivo]** → Operador intencionalmente reenvia a mesma mensagem em <5s. Improvável em uso normal. Se acontecer, basta esperar 5 segundos.
