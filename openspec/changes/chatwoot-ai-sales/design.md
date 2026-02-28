## Context

Projeto greenfield. Caio vende cursos de IA via WhatsApp Business (Evolution API já rodando num servidor). Volume baixo (dezenas de mensagens/dia), 1-2 operadores. O sistema é um copilot de vendas: recebe mensagens, propõe respostas com IA, o operador edita e envia. Não é um Chatwoot completo, é uma ferramenta focada no loop draft-edit-send.

## Goals / Non-Goals

**Goals:**
- Receber mensagens do WhatsApp via webhook e exibi-las numa inbox funcional
- Gerar drafts de resposta com Claude API usando contexto de vendas consultivas
- Permitir edição e envio rápido dos drafts
- Aprender com as edições do operador para melhorar os drafts ao longo do tempo
- Funcionar como ferramenta de trabalho diária: rápida, sem fricção

**Non-Goals:**
- UI bonita ou polida (funcional é suficiente)
- Multi-tenancy ou isolamento entre organizações
- RAG com vector database (inline é suficiente pro volume de docs)
- Automação sem supervisão humana (sempre human-in-the-loop)
- Suporte a mídia (áudio, imagem, vídeo) na v1
- Relatórios, métricas de SLA, dashboards

## Decisions

### D1: SQLite como banco de dados

SQLite via `aiosqlite` para acesso assíncrono. Volume baixo (dezenas de msgs/dia), 1-2 operadores, sem concorrência pesada. Não precisa de Postgres, Redis, nem nada distribuído. O banco fica num único arquivo, backup é copiar o arquivo, deploy é trivial.

**Alternativas consideradas:**
- PostgreSQL: overkill para o volume. Adiciona dependência de infra, conexão, migrations mais complexas
- JSON files: frágil demais para dados transacionais, sem queries

### D2: FastAPI com async para todo o backend

FastAPI com uvicorn. Um único processo serve a API REST (webhook, send, CRUD), os WebSockets (notificações em tempo real), e os arquivos estáticos do frontend. Sem separação em microserviços.

**Alternativas consideradas:**
- Flask: não tem suporte nativo a async e WebSocket
- Django: framework pesado demais para 4-5 endpoints

### D3: Geração de draft assíncrona via background task

Quando uma mensagem chega via webhook, o handler persiste no banco e dispara a geração de draft como uma `asyncio.Task`. O draft leva 2-5 segundos (latência da Claude API). Quando pronto, é salvo no banco e notificado ao frontend via WebSocket.

Não precisa de Celery, RQ, ou fila externa. `asyncio.create_task` é suficiente para o volume. Se o processo reiniciar no meio de uma geração, a mensagem já está salva e o draft pode ser regenerado manualmente.

### D4: Frontend em HTML + vanilla JS + WebSocket

Um único arquivo HTML com CSS inline e um arquivo JS. Sem React, Vue, build step, npm, bundler. O layout é um inbox de duas colunas: lista de conversas à esquerda, thread + textarea à direita.

WebSocket conecta ao backend para receber: novas mensagens, drafts gerados, confirmações de envio. O JS atualiza o DOM diretamente.

**Alternativas consideradas:**
- React/Next.js: build pipeline, node_modules, complexidade desproporcional
- htmx: boa opção, mas WebSocket puro é mais direto para o padrão de atualização contínua
- Streamlit: inadequado para interface de chat interativa

### D5: Prompt montado em camadas, sem RAG

O prompt para a Claude API é montado concatenando blocos nesta ordem:

```
1. System prompt (tom, postura de vendas, regras)
2. Knowledge base (todos os docs dos cursos + playbook, inline)
3. Few-shot examples (pares draft/final selecionados por relevância)
4. Histórico da conversa atual
5. Instrução final ("gere draft + justificativa")
```

Sem embedding, sem vector store, sem retrieval. Os docs dos 5 cursos + playbook cabem em ~4-5K tokens. Com Sonnet, o context window de 200K é mais que suficiente.

**Seleção de few-shot:** na v1, os 10 pares mais recentes. Quando o volume de edit pairs crescer, pode evoluir para seleção por similaridade textual simples (TF-IDF ou BM25 sobre a mensagem do cliente) sem precisar de embeddings.

### D6: Resposta estruturada com JSON para draft + justificativa

A Claude API é chamada com instrução para retornar JSON:
```json
{
  "draft": "texto da resposta proposta",
  "justification": "por que escolhi essa abordagem"
}
```

Isso separa cleanamente o draft (que vai pro textarea editável) da justificativa (que aparece como nota acima do textarea).

### D7: Edit pairs com flag de aceitação

Cada envio que teve um draft associado gera um registro:

| Campo | Tipo |
|---|---|
| id | INTEGER PK |
| conversation_id | FK |
| customer_message | TEXT |
| original_draft | TEXT |
| final_message | TEXT |
| was_edited | BOOLEAN |
| created_at | TIMESTAMP |

`was_edited = false` indica aceitação sem edição. Isso permite calcular acceptance rate e, no futuro, priorizar few-shot examples que foram aceitos sem edição (o modelo "acertou").

### D8: Modelo Claude Sonnet para drafts

Sonnet 4 (ou 4.6) para geração de drafts. Bom equilíbrio entre qualidade e custo/latência para o caso de uso. Opus seria melhor em nuances de vendas, mas a latência de 5-10s é ruim para o fluxo de trabalho. Com few-shot bons, Sonnet é suficiente.

A escolha do modelo fica configurável via variável de ambiente.

## Schema do Banco

```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT NOT NULL UNIQUE,
    contact_name TEXT,
    status TEXT DEFAULT 'active',  -- active, archived
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    evolution_message_id TEXT UNIQUE,  -- dedup
    direction TEXT NOT NULL,  -- inbound, outbound
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    trigger_message_id INTEGER NOT NULL REFERENCES messages(id),
    draft_text TEXT NOT NULL,
    justification TEXT,
    status TEXT DEFAULT 'pending',  -- pending, sent, discarded
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE edit_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    customer_message TEXT NOT NULL,
    original_draft TEXT NOT NULL,
    final_message TEXT NOT NULL,
    was_edited BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Estrutura de Arquivos

```
caiowoot/
├── app/
│   ├── main.py              # FastAPI app, startup, WebSocket manager
│   ├── config.py             # Settings (env vars: Evolution URL, API keys, model)
│   ├── database.py           # SQLite setup, migrations
│   ├── models.py             # Pydantic models
│   ├── routes/
│   │   ├── webhook.py        # POST /webhook (Evolution API)
│   │   ├── conversations.py  # GET /conversations, GET /conversations/{id}
│   │   └── messages.py       # POST /conversations/{id}/send
│   ├── services/
│   │   ├── draft_engine.py   # Prompt assembly + Claude API call
│   │   ├── evolution.py      # Evolution API client (send message)
│   │   └── knowledge.py      # Load/cache knowledge base files
│   └── static/
│       ├── index.html         # Single page app
│       └── app.js             # WebSocket + DOM manipulation
├── knowledge/
│   ├── curso-cdo.md
│   ├── curso-llm.md
│   ├── curso-atracao.md
│   ├── curso-ab-avancado.md
│   ├── curso-ai-influencers.md
│   └── playbook-vendas.md
├── pyproject.toml
└── .env
```

## Risks / Trade-offs

**[Single process, no queue] → Aceitável pro volume**
Se o processo cair no meio de uma geração de draft, o draft se perde. A mensagem já está salva. O operador pode clicar "regenerar" ou escrever manualmente. Para dezenas de msgs/dia, isso é aceitável. Se o volume crescer para centenas, considerar uma fila.

**[SQLite single-writer] → Aceitável para 1-2 operadores**
SQLite tem limitação de um writer por vez. Com 1-2 operadores e volume baixo, contenção é improvável. Se escalar para equipe maior, migrar para Postgres.

**[Few-shot por recência, não similaridade] → Bom o suficiente na v1**
Selecionar os 10 pares mais recentes é simples mas não ótimo. Pode incluir exemplos irrelevantes. Na prática, com conversas de vendas do mesmo domínio, a maioria dos exemplos recentes será relevante. Evoluir para BM25 quando houver 50+ pares.

**[Sem autenticação na v1] → Risco controlado**
A UI não terá login. Segurança via rede: rodar em localhost ou proteger com VPN/firewall. Suficiente para uso pessoal. Adicionar auth básico antes de dar acesso a outra pessoa.

**[Inline sem RAG] → Limite de ~50 páginas de docs**
Se a knowledge base crescer significativamente (novos cursos, muito conteúdo por curso), o inline vai estourar o budget de tokens no prompt. Para 5 cursos, folgado. Monitorar o tamanho total do prompt.

## Open Questions

- Qual o formato exato do webhook do Evolution API? (precisa inspecionar um payload real ou consultar a documentação da versão instalada)
- O Evolution API exige autenticação no webhook (API key no header) ou aceita qualquer POST?
- Como é o endpoint de envio de mensagem do Evolution API? (URL, formato do body, autenticação)
