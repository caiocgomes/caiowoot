## 1. Backend: Endpoints CRUD

- [x] 1.1 Criar `app/routes/knowledge.py` com router e validação de nome (regex `^[a-z0-9][a-z0-9-]*$`, rejeitar path traversal)
- [x] 1.2 Implementar GET /knowledge (listar docs: nome + mtime)
- [x] 1.3 Implementar GET /knowledge/{name} (ler conteúdo)
- [x] 1.4 Implementar POST /knowledge (criar doc, 409 se já existe, 422 se nome inválido)
- [x] 1.5 Implementar PUT /knowledge/{name} (atualizar conteúdo, 404 se não existe)
- [x] 1.6 Implementar DELETE /knowledge/{name} (remover doc, 404 se não existe)
- [x] 1.7 Registrar router no `app/main.py`

## 2. Frontend: Aba de Base de Conhecimento

- [x] 2.1 Adicionar toggle de abas no sidebar-header ("Conversas" / "Base de Conhecimento")
- [x] 2.2 Criar lista de documentos no sidebar (carregada via GET /knowledge)
- [x] 2.3 Criar área de edição no main: textarea monospace + botão salvar + botão deletar
- [x] 2.4 Implementar fluxo de criar novo documento (input de nome + textarea de conteúdo)
- [x] 2.5 Implementar fluxo de deletar com confirmação via confirm()
- [x] 2.6 Garantir que alternar entre abas preserva o estado (conversa ativa não se perde)

## 3. Testes

- [x] 3.1 Testes dos endpoints CRUD (happy path + erros: 404, 409, 422, path traversal)
