## Why

Hoje o sistema só gera drafts reativamente: quando o cliente manda uma mensagem. Mas o operador frequentemente precisa retomar uma conversa onde ele foi o último a falar (ex: enviou um PDF e disse "falo contigo depois"). Nesse cenário, o operador abre a conversa, vê que não tem draft, e precisa escrever do zero. O sistema já tem todo o contexto (histórico, knowledge base, exemplos) para sugerir uma continuação natural.

## What Changes

- Botão "Sugerir resposta" visível na área de compose quando não há drafts pendentes e a última mensagem da conversa é outbound
- Endpoint backend que dispara geração de drafts proativos (sem trigger_message_id de inbound)
- Prompt ajustado para gerar continuação ao invés de resposta a mensagem do cliente
- Frontend exibe os drafts normalmente após geração (mesmo fluxo dos drafts reativos)

## Capabilities

### New Capabilities

- `proactive-followup`: Capacidade de gerar drafts proativos quando o operador quer retomar uma conversa onde a última mensagem foi dele

### Modified Capabilities

- `draft-engine`: Ajustar prompt para suportar geração sem mensagem inbound como trigger, considerando a última mensagem outbound como contexto de continuação

## Impact

- `app/services/draft_engine.py`: Nova função ou parâmetro para geração proativa, instrução final do prompt condicional
- `app/routes/messages.py`: Novo endpoint para solicitar drafts proativos
- `app/static/app.js`: Botão "Sugerir resposta" e lógica de quando exibi-lo
- `app/static/index.html`: Markup do botão
- Schema do banco: `trigger_message_id` pode ser NULL ou apontar para outbound
