## 1. Reestruturar _build_prompt_parts

- [x] 1.1 Extrair knowledge base do user_content: `_build_prompt_parts` retorna `(user_content, situation_summary, rules_section, knowledge)` em vez de `(user_content, situation_summary, rules_section)`. O user_content nao inclui mais o bloco `## Base de conhecimento dos cursos`.
- [x] 1.2 Adicionar section de knowledge base no system prompt: criar helper `_build_knowledge_section()` que retorna o texto formatado da knowledge base para inclusao no system prompt.

## 2. Reestruturar _call_haiku com cache_control

- [x] 2.1 Mudar assinatura de `_call_haiku` para aceitar `knowledge: str` como parametro.
- [x] 2.2 Montar system como lista de 2 blocos: bloco 1 (base + rules + knowledge) com `cache_control: {"type": "ephemeral"}`, bloco 2 (approach modifier) sem cache.
- [x] 2.3 Logar metricas de cache (`cache_read_input_tokens`, `cache_creation_input_tokens`) apos cada chamada.

## 3. Atualizar generate_drafts e regenerate_draft

- [x] 3.1 Atualizar `generate_drafts` para receber knowledge de `_build_prompt_parts` e passar para `_call_haiku`.
- [x] 3.2 Atualizar `regenerate_draft` da mesma forma.
- [x] 3.3 Ajustar `save_prompt` para incluir knowledge no full_prompt logado.

## 4. Atualizar tests

- [x] 4.1 Atualizar `mock_claude_api` em conftest.py para refletir que system agora e lista de blocos (ajustar asserts que leem `call_kwargs["system"]`).
- [x] 4.2 Atualizar tests em `test_draft_engine_learning.py` que inspecionam system_prompt (extrair texto dos blocos).
- [x] 4.3 Atualizar tests em `test_attachment_suggestion.py` que verificam user_content (knowledge nao esta mais la).
- [x] 4.4 Rodar suite completa e verificar 206 tests passando.
