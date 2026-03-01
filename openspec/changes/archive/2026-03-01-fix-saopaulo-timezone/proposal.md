## Why

O sistema usa `datetime.now()` sem timezone em toda a camada Python. O SQLite grava timestamps via `CURRENT_TIMESTAMP` (UTC). O resultado: horários exibidos no contexto temporal do prompt (saudação, cálculo de "há quanto tempo", timestamps no histórico) refletem o fuso do servidor, não `America/Sao_Paulo`. Para um assistente WhatsApp que precisa dizer "Bom dia" ou "Desculpa a demora" no momento certo, isso quebra a experiência.

## What Changes

- Adicionar configuração `TIMEZONE` em `app/config.py` com default `America/Sao_Paulo`
- Substituir todos os `datetime.now()` por chamadas timezone-aware usando `zoneinfo.ZoneInfo`
- Ajustar `_build_temporal_context` e `_build_conversation_history` para operar no fuso configurado
- Converter timestamps do banco (UTC) para o fuso local ao exibir
- Padronizar `knowledge.py` para usar o mesmo fuso em vez de UTC hardcoded
- Atualizar testes para usar datetimes timezone-aware

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `draft-engine`: O contexto temporal (horário atual, cálculo de elapsed time, formato de timestamps no histórico) passa a usar o fuso `America/Sao_Paulo` em vez de datetime naive do sistema

## Impact

- `app/config.py`: novo campo `timezone`
- `app/services/draft_engine.py`: `_build_temporal_context`, `_build_conversation_history` (linhas 119, 128, 283-305)
- `app/routes/knowledge.py`: linha 42 (mtime conversion)
- `tests/test_temporal_context.py`: todos os testes que criam datetimes
- Sem novas dependências (usa `zoneinfo` da stdlib, Python 3.9+)
- Sem breaking changes em API
