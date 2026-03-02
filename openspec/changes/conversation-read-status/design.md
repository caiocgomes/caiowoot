## Context

A lista de conversas tem um único flag `has_unread` que indica "tem inbound depois do último outbound". Isso mistura dois estados distintos: mensagem que o operador nunca viu e mensagem que ele viu mas ainda não respondeu. O operador precisa distinguir visualmente os dois.

## Goals / Non-Goals

**Goals:**
- Distinguir "mensagem nova (não vista)" de "aguardando minha resposta (vista)"
- Rastreamento global de leitura (um `last_read_at` por conversa)
- Indicadores visuais claros na lista de conversas

**Non-Goals:**
- Rastreamento por operador (futuro, se necessário)
- Notificações push ou badges no ícone do app
- Marcar como não-lida manualmente

## Decisions

### 1. Coluna `last_read_at` na tabela `conversations`

Adicionar `last_read_at TIMESTAMP` na tabela `conversations`. Valor NULL = nunca aberta. Atualizar para `CURRENT_TIMESTAMP` quando o operador abre a conversa via `GET /conversations/{id}`.

Alternativa descartada: tabela separada `conversation_reads(conversation_id, operator_name, read_at)` para rastreamento por operador. Overengineering para o uso atual.

### 2. Dois flags na query de listagem

Substituir o `has_unread` por dois flags:

- `is_new`: EXISTS inbound com `created_at > COALESCE(last_read_at, '1970-01-01')` — mensagem que o operador nunca viu
- `needs_reply`: última mensagem da conversa é `direction = 'inbound'` — bola no campo do operador

A relação entre eles:
- `is_new=true` implica `needs_reply=true` (se tem mensagem nova, é inbound, então precisa responder)
- `needs_reply=true` NÃO implica `is_new=true` (pode ter visto mas não respondido)

### 3. Indicadores visuais

| Estado | `is_new` | `needs_reply` | Visual |
|--------|----------|---------------|--------|
| Mensagem nova | true | true | Bolinha verde + nome em negrito |
| Aguardando resposta | false | true | Nome em negrito |
| Respondido | false | false | Normal |

Substituir a borda azul esquerda (`.unread`) pelos novos indicadores.

### 4. Side-effect no GET de detalhe

`GET /conversations/{id}` atualiza `last_read_at` como side-effect. Não é RESTful puro, mas é o padrão mais simples e evita chamada extra do frontend. O endpoint já faz queries de leitura, um UPDATE adicional é negligível.

## Risks / Trade-offs

- [Side-effect em GET] → Aceitável dado a simplicidade. Se precisar de pureza REST no futuro, mover para POST /conversations/{id}/read.
- [Global vs. por operador] → Se dois operadores usarem simultaneamente, um "ver" zera para os dois. Aceitável no uso atual.
