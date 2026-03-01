## 1. Configuração

- [x] 1.1 Adicionar campo `timezone: str = "America/Sao_Paulo"` em `Settings` (`app/config.py`)
- [x] 1.2 Criar helper `now_local()` que retorna `datetime.now(ZoneInfo(settings.timezone))` em `app/config.py`

## 2. Draft Engine

- [x] 2.1 Substituir `datetime.now()` por `now_local()` em `_build_temporal_context` (`app/services/draft_engine.py:283`)
- [x] 2.2 Substituir `datetime.now()` por `now_local()` em `_build_conversation_history` (`app/services/draft_engine.py:119`)
- [x] 2.3 Converter timestamps do banco para timezone-aware ao parsear com `fromisoformat` em `_build_conversation_history` (linha 128) e `_build_temporal_context` (linha 289)

## 3. Knowledge

- [x] 3.1 Substituir `timezone.utc` por `ZoneInfo(settings.timezone)` em `app/routes/knowledge.py:42`

## 4. Testes

- [x] 4.1 Atualizar `tests/test_temporal_context.py` para usar datetimes timezone-aware com `ZoneInfo("America/Sao_Paulo")`
- [x] 4.2 Rodar testes e verificar que todos passam
