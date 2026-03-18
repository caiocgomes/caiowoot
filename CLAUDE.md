# CaioWoot

Copiloto de vendas WhatsApp: recebe mensagens via Evolution API, gera 3 variações de resposta (direta/consultiva/casual) via Claude Haiku, operador revisa e envia pela interface web.

## Stack

Python 3.12, FastAPI, aiosqlite (WAL), ChromaDB, Anthropic SDK, vanilla JS frontend (PWA).

## Commands

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload  # dev server
uv run pytest tests/ -v                                            # all tests
uv sync                                                            # install deps
```

## Architecture

1. **Request flow**: Evolution webhook → mensagem → `generate_drafts()` (3 variações paralelas) → WebSocket → operador envia
2. **Learning loop**: edit_pairs → strategic annotation → ChromaDB indexing → few-shot retrieval em próximos drafts
3. **Auto-qualifying**: bot estruturado com perguntas configuráveis, handoff automático após respostas ou 4 trocas
4. **Campaigns**: outreach em massa com variações A/B, rate limiting, retry, anti-hash de imagem
5. **Operator coaching**: análise periódica por conversa (erros factuais, engajamento, vendas recuperáveis) → digest por operador
6. **Scheduled sends**: agendamento de mensagens com executor em background (polling 10s)
7. **Prompt config**: prompts configuráveis via admin UI, hot-reload sem deploy

## Context routing

| Área | Arquivo |
|------|---------|
| Services (22 módulos) | `.claude/rules/services.md` |
| Routes e endpoints | `.claude/rules/routes.md` |
| Database e migrations | `.claude/rules/database.md` |
| Testes e fixtures | `.claude/rules/testing.md` |
| Frontend | `.claude/rules/frontend.md` |

## Common mistakes

- **Editar prompts no draft_engine**: prompt construction foi movido para `prompt_builder.py`. draft_engine só orquestra.
- **Chamar Anthropic direto**: usar `claude_client.py` (`call_haiku`, `get_anthropic_client`). Nunca instanciar cliente direto.
- **Esquecer patches de get_db nos testes**: cada módulo importa `get_db` diretamente. Patch precisa ser em cada módulo que usa, não só em `database.py`.
- **Confundir qualifying com draft**: qualifying usa `auto_qualifier.py` com QUALIFY_TOOL, não o draft_engine. São fluxos separados.
- **Ignorar background tasks**: scheduler e campaign_executor rodam como lifespan tasks. Testes que tocam envio devem mockar esses loops.
