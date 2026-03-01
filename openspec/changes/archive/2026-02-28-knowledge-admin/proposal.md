## Why

Hoje, adicionar ou atualizar informação na base de conhecimento exige criar/editar arquivos markdown manualmente na pasta `knowledge/`. Para mudanças rápidas (atualizar preço de uma promoção, adicionar resposta a uma pergunta que se repete), essa fricção faz com que o operador simplesmente não atualize a base, e o Haiku continua respondendo com informação desatualizada.

## What Changes

- Novos endpoints REST para CRUD completo dos documentos da base de conhecimento (`knowledge/*.md`)
- Nova aba "Base de Conhecimento" na interface do operador, com lista de documentos, editor de texto e criação de novos documentos
- O mecanismo existente de hot-reload por mtime no `knowledge.py` continua funcionando sem alteração

## Capabilities

### New Capabilities
- `knowledge-admin`: Endpoints REST e interface web para listar, criar, editar e deletar documentos markdown da base de conhecimento

### Modified Capabilities
(nenhuma)

## Impact

- **Backend**: Novo módulo de rotas `app/routes/knowledge.py` com endpoints CRUD
- **Frontend**: Nova aba/seção no `app/static/index.html` e `app/static/app.js`
- **`app/main.py`**: Registro do novo router
- **Dependências**: Nenhuma nova. Leitura e escrita de arquivos com `pathlib`, que já é usado no `knowledge.py`
- **Segurança**: Os endpoints operam apenas dentro da pasta `knowledge/`, validando que o path não escape (path traversal)
