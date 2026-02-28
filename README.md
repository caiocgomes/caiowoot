# CaioWoot

Copiloto de vendas para WhatsApp com IA. Recebe mensagens de clientes via Evolution API, gera 3 variações de resposta usando Claude Haiku em paralelo, e apresenta numa interface web para o operador revisar, editar e enviar.

## Como funciona

1. Cliente manda mensagem no WhatsApp
2. Evolution API envia webhook para o CaioWoot
3. Claude Haiku gera 3 variações de resposta (direta, consultiva, casual) em paralelo
4. Operador vê as 3 opções na interface, seleciona uma, edita se quiser, e envia
5. Todas as edições ficam registradas como edit pairs para tuning futuro do modelo

## Stack

- **Backend**: FastAPI + aiosqlite
- **IA**: Claude Haiku (3 variações paralelas via asyncio.gather)
- **WhatsApp**: Evolution API v2
- **Frontend**: HTML/JS vanilla (sem framework)
- **WebSocket**: atualizações em tempo real

## Funcionalidades

- **3 variações de draft**: cada mensagem gera 3 respostas com abordagens diferentes
- **Regeneração**: regenerar uma variação individual ou todas, com instrução opcional para a IA
- **Barra de instrução**: operador pode dar contexto/direção para a IA (ex: "foca no preço", "ela é técnica")
- **Anexos**: envio de imagens e documentos junto com a mensagem
- **Few-shot learning**: edições do operador viram exemplos para futuras gerações
- **Prompt logging**: prompts salvos em disco com hash SHA-256 para rastreabilidade e tuning
- **Edit pairs**: registro completo de cada interação (draft original, mensagem final, se foi editada, qual variação escolhida)

## Setup

```bash
# Instalar dependências
uv sync

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas chaves

# Rodar
uv run uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

### Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `EVOLUTION_API_URL` | URL da Evolution API |
| `EVOLUTION_API_KEY` | Chave da Evolution API |
| `EVOLUTION_INSTANCE` | Nome da instância no Evolution |
| `ANTHROPIC_API_KEY` | Chave da API Anthropic |
| `CLAUDE_HAIKU_MODEL` | Modelo Haiku (default: claude-haiku-4-5-20251001) |
| `DATABASE_PATH` | Caminho do SQLite (default: data/caiowoot.db) |

## Testes

```bash
uv run pytest tests/ -v
```

## Estrutura

```
app/
  main.py                  # FastAPI app + WebSocket
  config.py                # Settings via pydantic
  database.py              # Schema SQLite + init
  models.py                # Pydantic models
  websocket_manager.py     # Broadcast para frontend
  routes/
    webhook.py             # Recebe mensagens do WhatsApp
    conversations.py       # Lista e detalha conversas
    messages.py            # Envio + regeneração de drafts
  services/
    draft_engine.py        # Geração de 3 variações com Haiku
    evolution.py           # Integração com Evolution API
    knowledge.py           # Carrega base de conhecimento
    prompt_logger.py       # Salva prompts em disco
  static/
    index.html             # Interface do operador
    app.js                 # Lógica do frontend
knowledge/                 # Markdown com info dos cursos
data/                      # SQLite + prompts + anexos
```
