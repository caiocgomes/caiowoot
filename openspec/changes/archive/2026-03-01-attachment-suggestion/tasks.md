## 1. Banco e storage

- [x] 1.1 Adicionar migration para coluna `attachment_filename TEXT` na tabela `edit_pairs`
- [x] 1.2 Criar diretório `knowledge/attachments/` e mover handbooks existentes de `data/attachments/` para lá com nomes descritivos

## 2. Endpoints de anexos

- [x] 2.1 Criar `GET /api/attachments` que lista filenames de `knowledge/attachments/` (requer auth)
- [x] 2.2 Criar `GET /api/attachments/<filename>` que serve o arquivo (requer auth, valida path traversal)

## 3. Captura de anexo no edit_pair

- [x] 3.1 Modificar `routes/messages.py` para extrair o filename do anexo enviado e gravar `attachment_filename` no INSERT do edit_pair

## 4. Draft engine

- [x] 4.1 Criar função `list_known_attachments()` que lê `knowledge/attachments/` e retorna lista de filenames
- [x] 4.2 Adicionar seção "Anexos disponíveis" no user prompt com os filenames retornados
- [x] 4.3 Atualizar instruções no system prompt para orientar a LLM sobre quando e como sugerir anexos via campo `suggested_attachment`
- [x] 4.4 Modificar `_parse_response` para extrair `suggested_attachment` do JSON e retornar junto com draft e justification
- [x] 4.5 Validar `suggested_attachment` contra arquivos existentes em `knowledge/attachments/` (descartar se não existe)
- [x] 4.6 Incluir `suggested_attachment` no payload de `drafts_ready` enviado via WebSocket

## 5. Few-shot com informação de anexo

- [x] 5.1 Modificar `_build_fewshot_from_retrieval` para incluir `Anexo enviado: <filename>` nos exemplos onde `attachment_filename` não é NULL
- [x] 5.2 Modificar `_build_fewshot_fallback` para incluir informação de anexo da mesma forma

## 6. Strategic annotation

- [x] 6.1 Modificar `generate_annotation` para aceitar parâmetro `attachment_filename` e incluir no user content quando presente
- [x] 6.2 Modificar chamada em `routes/messages.py` para passar `attachment_filename` ao `generate_annotation`

## 7. Frontend

- [x] 7.1 Modificar `showDrafts` em `app.js` para exibir indicador de sugestão de anexo quando `suggested_attachment` está presente no draft
- [x] 7.2 Implementar botão "Anexar" na sugestão que carrega o arquivo via `GET /api/attachments/<filename>` e pré-popula o campo de attachment

## 8. Testes

- [x] 8.1 Testes de endpoint: `GET /api/attachments` lista arquivos, `GET /api/attachments/<filename>` serve arquivo, path traversal bloqueado, 401 sem auth
- [x] 8.2 Testes de edit_pair: `attachment_filename` gravado quando operador envia com anexo, NULL quando sem anexo
- [x] 8.3 Testes de draft engine: `suggested_attachment` extraído do JSON, validação contra arquivos existentes, seção "Anexos disponíveis" no prompt
- [x] 8.4 Testes de few-shot: exemplos incluem `Anexo enviado:` quando edit_pair tem attachment_filename
- [x] 8.5 Testes de strategic annotation: `attachment_filename` incluído no user content da annotation
