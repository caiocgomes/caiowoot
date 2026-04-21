## 1. Prompt builder

- [x] 1.1 Adicionar parâmetro opcional `trigger_message_id: int | None = None` à assinatura de `build_prompt_parts` em `app/services/prompt_builder.py`.
- [x] 1.2 Nova função helper `_load_post_trigger_outbounds(db, conversation_id, trigger_message_id)` que retorna lista de dicts com `content`, `created_at`, `sent_by` das outbounds com `id >= trigger_message_id` (ou `created_at >= trigger_message.created_at`, o que for mais preciso no schema) ordenadas cronologicamente. Retorna lista vazia se `trigger_message_id` é None ou não existe.
- [x] 1.3 No corpo de `build_prompt_parts`, quando `trigger_message_id` é dado e há outbounds, formatar a seção `"## Respostas já enviadas neste turno"` com cada outbound em uma linha (timestamp + texto) e inserir no `user_content` logo antes do bloco de histórico, e reescrever `final_instruction` conforme o spec.
- [x] 1.4 Quando `proactive=True`, ignorar a nova seção e manter instrução proactive atual.
- [x] 1.5 Quando `trigger_message_id` é None ou não há outbounds posteriores, manter fluxo original byte-a-byte (sem seção nova, instrução original).

## 2. Draft engine

- [x] 2.1 Em `app/services/draft_engine.py`, `generate_drafts` passa `trigger_message_id` para `build_prompt_parts` (via `_build_prompt_parts` interno).
- [x] 2.2 Em `regenerate_draft` (mesmo arquivo), passar `trigger_message_id` adiante.
- [x] 2.3 Verificar se há outros calls internos a `_build_prompt_parts` em `draft_engine.py`; propagar `trigger_message_id` onde disponível.

## 3. Testes

- [x] 3.1 Novo arquivo `tests/test_regenerate_with_partial_response.py`. Seed conversa com inbound + uma outbound subsequente do operador. Mock Haiku capturando o `user_content` da chamada. Asserir que user_content contém a string "Respostas já enviadas neste turno", o texto da outbound, e a nova instrução complementar.
- [x] 3.2 Teste: regenerate SEM outbound intermediária. Asserir que user_content NÃO contém "Respostas já enviadas" e instrução original é preservada.
- [x] 3.3 Teste: múltiplas outbounds intermediárias. Asserir ordem cronológica na seção.
- [x] 3.4 Teste: `proactive=True` nunca adiciona a seção, independente de outbounds.
- [x] 3.5 Teste: caller que não passa `trigger_message_id` (ex: call manual sem arg) preserva comportamento legado.
- [x] 3.6 Ajustar/verificar `tests/test_regenerate.py` existente não quebra com a mudança.

## 4. Qualidade

- [x] 4.1 `uv run pytest tests/ --ignore=tests/e2e -q` verde.
- [ ] 4.2 Rodar `uv run uvicorn` localmente; em uma conversa de teste, mandar resposta, disparar regenerate, validar que as 3 novas variações NÃO repetem o que já foi enviado.
- [ ] 4.3 Commit com mensagem descritiva e push.
