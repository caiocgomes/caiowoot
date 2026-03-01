## 1. Contexto do nome no prompt

- [x] 1.1 Em `_build_prompt_parts`, buscar `contact_name` da conversa no banco e extrair o primeiro nome via `split()[0]`
- [x] 1.2 Incluir seção `## Cliente\nNome: {primeiro_nome}` no `user_content`, antes da conversa atual (omitir se nome vazio)
- [x] 1.3 Adicionar no `SYSTEM_PROMPT` orientação sobre uso natural do nome ("Se souber o nome do cliente, use-o ocasionalmente de forma natural. Não repita o nome em toda mensagem.")

## 2. Campo de edição maior

- [x] 2.1 No CSS de `#draft-input`, alterar `min-height` de `120px` para `200px` e `max-height` de `300px` para `500px`
- [x] 2.2 Na função `autoResize` em `app.js`, alterar o limite de `300` para `500` no `Math.min`

## 3. Testes

- [x] 3.1 Atualizar fixtures/testes de `_build_prompt_parts` para incluir `contact_name` na conversa e verificar que o primeiro nome aparece no prompt gerado
- [x] 3.2 Adicionar teste para `contact_name` vazio: prompt gerado não deve conter seção de nome
