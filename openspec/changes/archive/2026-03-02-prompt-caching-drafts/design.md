## Context

As 3 chamadas paralelas de draft (`_call_haiku`) enviam o system prompt como string unica concatenando: base (postura/tom/regras/sections fixas) + rules_section + approach_modifier. O user_content inclui knowledge base (~4260 tokens), few-shot, historico e contexto temporal. Tudo identico entre as 3 calls exceto o approach_modifier (~50 tokens).

O prompt caching da Anthropic exige que o system prompt seja enviado como lista de blocos (dicts) em vez de string. Blocos marcados com `cache_control: {"type": "ephemeral"}` sao cacheados por 5 minutos. O minimo cacheavel para Haiku 4.5 e 2048-4096 tokens.

O system prompt base tem ~800-1200 tokens, abaixo do minimo. A knowledge base (~4260 tokens) precisa ser incorporada ao system para ultrapassar o limite.

## Goals / Non-Goals

**Goals:**
- Cachear o prefixo compartilhado (system base + rules + knowledge) entre as 3 chamadas de draft
- Obter cache hits cross-conversation quando mensagens sao processadas dentro do TTL de 5 min
- Logar metricas de cache (write/read tokens) para validar economia

**Non-Goals:**
- Cachear chamadas de situation_summary ou strategic_annotation (chamadas unicas, prompts curtos)
- Consolidar as 3 calls em 1 (otimizacao separada)
- Mudar modelo ou parametros de geracao

## Decisions

### 1. Knowledge base migra para o system prompt

A knowledge base sai do user_content e vai para o system prompt. Isso garante que o bloco cacheavel tenha ~5000-5500 tokens (system base ~1000 + knowledge ~4260), acima de qualquer minimo.

Alternativa considerada: cachear user_content. Nao funciona porque o cache de messages e invalidado quando o system muda (approach modifier diferente entre as 3 calls).

### 2. System prompt vira lista de 2 blocos

```python
system = [
    {"type": "text", "text": base + rules + knowledge, "cache_control": {"type": "ephemeral"}},
    {"type": "text", "text": f"\n\n## Estilo desta variacao\n{approach_modifier}"},
]
```

Bloco 1 (cacheavel): identico entre as 3 calls e estavel cross-conversation.
Bloco 2 (nao cacheavel): approach modifier, diferente por call.

### 3. `_build_prompt_parts` retorna knowledge separadamente

Assinatura muda de retornar `(user_content, situation_summary, rules_section)` para `(user_content, situation_summary, rules_section, knowledge)`. O user_content nao inclui mais a knowledge base.

### 4. `_call_haiku` aceita knowledge como parametro

Assinatura muda para `_call_haiku(user_content, approach_modifier, system_prompt, rules_section, knowledge)`. Monta o system como lista de blocos internamente.

### 5. Logging de metricas de cache

Apos cada chamada, logar `response.usage.cache_read_input_tokens` e `response.usage.cache_creation_input_tokens` para validar que o cache esta funcionando.

## Risks / Trade-offs

**Knowledge no system prompt muda a semantica do prompt** - Risco baixo. A knowledge base e material de referencia, semanticamente valido tanto em system quanto user. Muitas apps de RAG fazem isso por motivos de cache.

**Minimo de tokens pode nao ser atingido com knowledge base pequena** - Se o knowledge base encolher significativamente (<1000 tokens), o bloco cacheavel pode ficar abaixo do minimo. Mitigation: o cache e silenciosamente ignorado nesse caso, sem erro. O sistema funciona normalmente, apenas sem o beneficio de cache.

**Tests que inspecionam system prompt precisam adaptar** - Tests que fazem `call_kwargs["system"]` e esperam string precisam lidar com lista de blocos. Mitigation: criar helper de extracao do system text nos tests.
