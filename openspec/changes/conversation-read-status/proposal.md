## Why

A lista de conversas não distingue entre "mensagem nova que não vi" e "cliente respondeu mas eu já vi e ainda não respondi". Hoje só existe um flag (`has_unread`) que mistura os dois. O operador precisa saber de relance o que é urgente (novo) vs. o que está pendente (bola comigo).

## What Changes

- Adicionar coluna `last_read_at` na tabela `conversations` para rastrear quando o operador viu a conversa
- Atualizar `last_read_at` quando o operador abre uma conversa (`GET /conversations/{id}`)
- Retornar dois flags na listagem: `is_new` (inbound depois de `last_read_at`) e `needs_reply` (última mensagem é inbound)
- Frontend: bolinha verde + negrito para `is_new`, só negrito para `needs_reply`, normal quando bola está com o cliente

## Capabilities

### New Capabilities
- `conversation-read-status`: Rastreamento de leitura de conversas e indicadores visuais na lista

### Modified Capabilities
- `inbox-ui`: Adicionar indicadores visuais (bolinha verde, negrito) baseados nos novos flags `is_new` e `needs_reply`

## Impact

- `app/database.py`: nova coluna + migration
- `app/routes/conversations.py`: atualizar query de listagem e endpoint de detalhe
- `app/static/index.html`: CSS para os novos estados visuais
- `app/static/app.js`: renderizar os indicadores baseados nos flags
