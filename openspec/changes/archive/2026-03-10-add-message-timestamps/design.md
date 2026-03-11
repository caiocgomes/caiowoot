## Context

Mensagens no chat não mostram horário. O campo `created_at` já existe na tabela `messages` e a API já retorna via `SELECT *`. A função `formatTime()` em `app.js` já converte timestamps UTC para `America/Sao_Paulo`, retornando HH:MM para hoje e DD/MM para dias anteriores. As mensagens usam layout flex com `.msg.inbound` alinhado à esquerda e `.msg.outbound` à direita.

## Goals / Non-Goals

**Goals:**
- Mostrar horário em cada mensagem do chat
- Separar visualmente mensagens de dias diferentes
- Reutilizar `formatTime()` existente para consistência

**Non-Goals:**
- Não mudar o backend (dados já disponíveis)
- Não adicionar status de leitura (visto/entregue)
- Não mostrar segundos no horário

## Decisions

**1. Timestamp dentro do balão da mensagem**

Horário como elemento inline no canto inferior direito do balão (padrão WhatsApp). Alternativa seria fora do balão, mas polui visualmente e quebra o agrupamento.

**2. Reutilizar `formatTime()` para separadores de data, criar `formatTimeShort()` para horário das mensagens**

`formatTime()` retorna HH:MM para hoje e DD/MM para outros dias. Para o horário dentro do balão, queremos sempre HH:MM. Para os separadores entre dias, queremos data por extenso (ex: "03 de março"). Criar uma função auxiliar simples para cada caso em vez de sobrecarregar a existente.

**3. Separador de data como div centralizado entre mensagens**

Div com texto centralizado e linhas laterais (padrão apps de mensagem). Inserido por `appendMessage()` quando o dia da mensagem atual difere do dia da anterior.

## Risks / Trade-offs

**Mensagens sem `created_at`** → Possível em mensagens legadas ou edge cases. Mitigação: não renderizar timestamp se `msg.created_at` for null.

**Performance com muitas mensagens** → `appendMessage()` já é chamado N vezes ao abrir conversa. Adicionar um `new Date()` por mensagem é negligível.
