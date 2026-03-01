## Why

Caio vende cursos de IA (CDO, Senhor das LLMs, Atração, AB Avançado, AI para Influencers) via WhatsApp Business usando Evolution API. As conversas são de vendas consultivas: qualificar o lead, lidar com objeções, direcionar pro curso certo. Ele quer manter o tom pessoal ("parecer que sou eu respondendo") mas não tem tempo de redigir cada mensagem com a atenção necessária. Precisa de um copilot que proponha a resposta e ele edite/envie.

## What Changes

- Novo sistema web que recebe mensagens do WhatsApp via webhook do Evolution API e exibe numa inbox
- Draft engine que gera propostas de resposta usando Claude API, alimentado por: documentação dos cursos, histórico da conversa, e exemplos de edições passadas (few-shot learning)
- UI funcional (não precisa ser bonita) com lista de conversas, thread de mensagens, draft editável e botão de envio
- Loop de aprendizado: cada par (draft da IA, mensagem final enviada) é armazenado e usado como few-shot para calibrar tom e estratégia de vendas
- Envio de mensagens de volta via Evolution API
- Base de conhecimento com ementas, preços, FAQs e estratégias de vendas (objeções comuns, padrões de conversa que convertem)

## Capabilities

### New Capabilities

- `webhook-receiver`: Recebe e processa mensagens do Evolution API via webhook, persiste conversas no banco
- `draft-engine`: Gera drafts de resposta usando Claude API com contexto da conversa, base de conhecimento dos cursos e few-shot examples das edições passadas. Inclui justificativa curta da abordagem escolhida
- `inbox-ui`: Interface web funcional com lista de conversas, thread de mensagens, draft editável e envio. Atualização em tempo real via WebSocket
- `message-sender`: Envia mensagens de volta ao WhatsApp via Evolution API e registra o par (draft, mensagem final) para o loop de aprendizado
- `knowledge-base`: Armazenamento e retrieval da documentação dos cursos, preços, FAQs e playbook de vendas. Inicialmente inline no prompt (sem RAG), com possibilidade de evoluir

### Modified Capabilities

Nenhuma. Projeto greenfield.

## Impact

- **APIs externas**: Evolution API (webhook de entrada + endpoint de envio), Claude API (geração de drafts)
- **Infra**: FastAPI + SQLite no mesmo servidor ou VPS próximo ao Evolution API
- **Frontend**: HTML + vanilla JS + WebSocket, sem framework
- **Dependências Python**: fastapi, uvicorn, httpx, anthropic, sqlite (stdlib)
- **Dados**: conversas exportadas do WhatsApp comercial como seed inicial para few-shot examples
