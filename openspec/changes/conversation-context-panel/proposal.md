## Why

Quando o operador volta a uma conversa depois de horas ou dias, precisa reler o histórico inteiro pra lembrar qual produto o cliente quer, se já enviou handbook, se já mandou link de compra. Com volume alto de conversas isso é inviável. Falta um resumo estruturado e persistente do estado de cada lead no funil de vendas.

## What Changes

- Adicionar colunas `funnel_product` e `funnel_stage` na tabela `conversations` para rastrear produto de interesse e etapa do funil
- Estender `generate_situation_summary()` para extrair produto e etapa de forma estruturada junto com o resumo textual
- Atualizar automaticamente o funil da conversa quando novos drafts são gerados (IA como copilot)
- Painel lateral direito no desktop mostrando produto, etapa do funil e resumo da conversa
- Operador pode corrigir produto e etapa com clique quando a IA erra
- Endpoint para atualizar manualmente o funil de uma conversa
- Retornar dados do funil no `GET /conversations` e `GET /conversations/{id}`

## Capabilities

### New Capabilities
- `conversation-funnel`: Rastreamento de produto de interesse e etapa do funil por conversa, com atualização automática via IA e correção manual pelo operador
- `context-panel-ui`: Painel lateral direito no desktop exibindo produto, etapa e resumo da conversa, com controles para correção manual

### Modified Capabilities
- `situation-summary`: Estender para extrair produto e etapa de forma estruturada além do resumo textual
- `inbox-ui`: Retornar `funnel_product` e `funnel_stage` na listagem de conversas

## Impact

- `app/database.py`: novas colunas + migration
- `app/services/situation_summary.py`: retornar JSON estruturado com produto + etapa + resumo
- `app/services/draft_engine.py`: salvar produto e etapa extraídos na conversa
- `app/routes/conversations.py`: endpoint PATCH para atualizar funil, incluir dados no GET
- `app/static/index.html`: layout do painel direito, CSS
- `app/static/app.js`: renderizar painel, handlers de edição manual
