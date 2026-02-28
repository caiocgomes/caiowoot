## 1. Project Setup

- [x] 1.1 Inicializar projeto com `uv init`, criar `pyproject.toml` com dependências (fastapi, uvicorn, aiosqlite, httpx, anthropic)
- [x] 1.2 Criar `.env.example` com variáveis: `EVOLUTION_API_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE`, `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `DATABASE_PATH`
- [x] 1.3 Criar `app/config.py` com Pydantic Settings carregando do `.env`
- [x] 1.4 Criar estrutura de diretórios: `app/routes/`, `app/services/`, `app/static/`, `knowledge/`

## 2. Database

- [x] 2.1 Criar `app/database.py` com setup do SQLite via aiosqlite: init, get_db, create_tables
- [x] 2.2 Implementar schema SQL (conversations, messages, drafts, edit_pairs) conforme design.md
- [x] 2.3 Criar `app/models.py` com Pydantic models: Conversation, Message, Draft, EditPair

## 3. Webhook Receiver

- [x] 3.1 Pesquisar formato do webhook do Evolution API (documentação ou payload real) para mapear os campos corretos
- [x] 3.2 Criar `app/routes/webhook.py` com endpoint POST /webhook que recebe payload do Evolution API
- [x] 3.3 Implementar extração de campos (phone, name, text, message_id, timestamp) e filtragem de eventos não-mensagem
- [x] 3.4 Implementar dedup por evolution_message_id e criação/atualização de conversation
- [x] 3.5 Disparar geração de draft via asyncio.create_task após persistir mensagem

## 4. Evolution API Client

- [x] 4.1 Criar `app/services/evolution.py` com client httpx para enviar mensagens via Evolution API
- [x] 4.2 Implementar método send_text_message(phone_number, text) com tratamento de erro

## 5. Knowledge Base

- [x] 5.1 Criar `app/services/knowledge.py` com loader que lê todos os .md de `knowledge/`
- [x] 5.2 Criar arquivos iniciais na pasta `knowledge/`: um .md por curso (CDO, LLM, Atração, AB Avançado, AI Influencers) com ementa, preço, público, formato, diferenciais
- [x] 5.3 Criar `knowledge/playbook-vendas.md` com objeções comuns, estratégias de qualificação, ancoragem de preço, comparativos

## 6. Draft Engine

- [x] 6.1 Criar `app/services/draft_engine.py` com função principal generate_draft(conversation_id)
- [x] 6.2 Implementar montagem do prompt em camadas: system prompt → knowledge base → few-shot → histórico da conversa → instrução final
- [x] 6.3 Escrever system prompt com postura de vendas consultivas, tom do Caio, regras de comportamento
- [x] 6.4 Implementar seleção de few-shot: buscar os 10 edit_pairs mais recentes e formatar como exemplos
- [x] 6.5 Implementar chamada à Claude API com resposta JSON estruturada (draft + justification)
- [x] 6.6 Persistir draft no banco e notificar frontend via WebSocket

## 7. Message Sender

- [x] 7.1 Criar `app/routes/messages.py` com endpoint POST /conversations/{id}/send
- [x] 7.2 Implementar envio via Evolution API client e persistência da mensagem outbound
- [x] 7.3 Implementar gravação do edit_pair: comparar draft original com mensagem final, setar was_edited
- [x] 7.4 Notificar frontend via WebSocket após envio bem-sucedido

## 8. WebSocket Manager

- [x] 8.1 Criar WebSocket manager em `app/main.py`: connection registry, broadcast por conversation
- [x] 8.2 Implementar endpoint WS /ws com tipos de evento: new_message, draft_ready, message_sent, error

## 9. Frontend

- [x] 9.1 Criar `app/static/index.html` com layout de duas colunas: sidebar (lista de conversas) + main (thread + textarea)
- [x] 9.2 Criar `app/static/app.js` com conexão WebSocket e handlers para cada tipo de evento
- [x] 9.3 Implementar lista de conversas: fetch GET /conversations, renderizar com nome/preview/timestamp/unread indicator
- [x] 9.4 Implementar thread de mensagens: fetch GET /conversations/{id}, renderizar com distinção visual inbound/outbound
- [x] 9.5 Implementar área de draft: textarea editável + justificativa da IA acima + botão enviar
- [x] 9.6 Implementar envio: POST /conversations/{id}/send com conteúdo do textarea, limpar textarea após sucesso
- [x] 9.7 Implementar atualizações em tempo real: novo message no thread, draft no textarea, conversation list reorder

## 10. FastAPI App e Static Files

- [x] 10.1 Criar `app/main.py` com FastAPI app, incluir routers, montar static files, startup event para init DB e carregar knowledge base
- [ ] 10.2 Testar fluxo completo: simular webhook → ver mensagem na UI → ver draft → editar → enviar → verificar edit_pair salvo

## 11. Test Setup

- [x] 11.1 Adicionar dependências de teste ao pyproject.toml: pytest, pytest-asyncio, httpx (TestClient)
- [x] 11.2 Criar `tests/conftest.py` com fixtures: test database (SQLite in-memory), FastAPI TestClient, mock Evolution API (httpx mock), mock Claude API

## 12. Tests: Webhook Receiver

- [x] 12.1 Test: mensagem de texto recebida via webhook persiste no banco com phone, text, timestamp, message_id
- [x] 12.2 Test: evento de status update (não-mensagem) retorna 200 e não persiste nada
- [x] 12.3 Test: mensagem duplicada (mesmo message_id) retorna 200 e não cria registro duplicado
- [x] 12.4 Test: primeira mensagem de um phone novo cria conversation + message
- [x] 12.5 Test: mensagem de phone existente adiciona message à conversation existente
- [x] 12.6 Test: mensagem recebida dispara geração de draft (verificar que draft é criado no banco)

## 13. Tests: Draft Engine

- [x] 13.1 Test: generate_draft monta prompt com system prompt, knowledge base, histórico da conversa e chama Claude API (mock)
- [x] 13.2 Test: resposta da Claude API é parseada como JSON com campos draft e justification
- [x] 13.3 Test: draft é persistido no banco com status 'pending' e associado à mensagem trigger
- [x] 13.4 Test: few-shot examples são incluídos no prompt quando existem edit_pairs no banco
- [x] 13.5 Test: sem edit_pairs, prompt é montado sem few-shot (cold start)
- [x] 13.6 Test: máximo de 10 few-shot examples selecionados (os mais recentes)

## 14. Tests: Message Sender

- [x] 14.1 Test: POST /conversations/{id}/send envia mensagem via Evolution API (mock) e persiste como outbound
- [x] 14.2 Test: falha no Evolution API retorna erro e não persiste mensagem
- [x] 14.3 Test: envio com draft editado cria edit_pair com was_edited=true
- [x] 14.4 Test: envio com draft sem edição cria edit_pair com was_edited=false
- [x] 14.5 Test: envio manual (sem draft associado) não cria edit_pair

## 15. Tests: Knowledge Base

- [x] 15.1 Test: loader carrega todos os .md do diretório knowledge/ e retorna conteúdo concatenado
- [x] 15.2 Test: diretório vazio retorna string vazia sem erro
- [x] 15.3 Test: arquivo modificado é recarregado na próxima chamada

## 16. Tests: API Endpoints (integração)

- [x] 16.1 Test: GET /conversations retorna lista ordenada por última mensagem
- [x] 16.2 Test: GET /conversations/{id} retorna conversa com todas as mensagens e draft pendente
- [x] 16.3 Test: fluxo completo: webhook recebe msg → draft gerado → GET retorna draft → POST send → edit_pair criado
