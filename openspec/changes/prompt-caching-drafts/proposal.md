## Why

As 3 chamadas paralelas de draft enviam ~99% do mesmo conteudo (system prompt + knowledge base + few-shot + historico), diferindo apenas no approach modifier (~50 tokens). Isso triplica o custo de input sem necessidade. Com prompt caching da Anthropic, o prefixo compartilhado e escrito no cache uma vez e lido a 10x mais barato nas chamadas seguintes. Economia estimada de ~50% no input das chamadas de draft.

## What Changes

- Mover knowledge base do user_content (messages) para o system prompt, garantindo que o bloco cacheavel ultrapasse o minimo de 2048-4096 tokens exigido pelo Haiku 4.5
- Reestruturar `_call_haiku` para montar o system prompt como lista de blocos (em vez de string), com `cache_control: {"type": "ephemeral"}` no bloco compartilhado
- Separar o approach modifier como segundo bloco do system (sem cache), permitindo que o prefixo identico entre as 3 calls gere cache hits
- Extrair knowledge base como retorno separado de `_build_prompt_parts` para que `generate_drafts` e `regenerate_draft` possam passa-lo ao system prompt
- Monitorar cache hits via `response.usage.cache_read_input_tokens` e `cache_creation_input_tokens` nos logs

## Capabilities

### New Capabilities
- `prompt-caching`: Configuracao de prompt caching da Anthropic nas chamadas de draft, incluindo reestruturacao do system prompt em blocos com cache_control e monitoramento de cache hits

### Modified Capabilities
- `draft-engine`: Knowledge base migra do user_content para o system prompt; `_call_haiku` passa a receber system como lista de blocos; `_build_prompt_parts` retorna knowledge separadamente

## Impact

- `app/services/draft_engine.py`: reestruturacao de `_call_haiku`, `_build_prompt_parts`, `generate_drafts`, `regenerate_draft`
- `tests/conftest.py`: mock_claude_api precisa refletir system como lista de blocos
- `tests/test_draft_engine_learning.py`, `tests/test_regenerate.py`, `tests/test_attachment_suggestion.py`: ajustar asserts que inspecionam system prompt (agora e lista, nao string)
