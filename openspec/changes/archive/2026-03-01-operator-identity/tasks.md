## 1. Config e banco

- [x] 1.1 Adicionar `OPERATORS` (lista csv) e `operators` (parsed list) em `config.py`
- [x] 1.2 Adicionar migration para coluna `sent_by TEXT` na tabela `messages`

## 2. Auth e sessão

- [x] 2.1 Modificar `create_session_cookie` para aceitar e incluir `operator` no payload
- [x] 2.2 Criar função `get_operator_from_cookie(request)` que extrai o nome do operador da sessão
- [x] 2.3 Modificar middleware para invalidar sessão sem `operator` quando `OPERATORS` está configurado
- [x] 2.4 Criar endpoint `GET /api/me` que retorna o operador da sessão
- [x] 2.5 Modificar endpoint `POST /login` para aceitar `operator` no body e validar contra a lista configurada

## 3. Mensagens

- [x] 3.1 Modificar `send_message` em `routes/messages.py` para extrair operador da sessão e gravar `sent_by` no INSERT
- [x] 3.2 Modificar `GET /conversations` para retornar `last_responder` (nome do operador do último outbound de cada conversa)

## 4. Frontend

- [x] 4.1 Adicionar campo de seleção de operador na tela de login (`login.html`) com lista carregada via endpoint
- [x] 4.2 Criar endpoint `GET /api/operators` que retorna a lista de operadores configurados (público, pré-auth)
- [x] 4.3 Exibir `last_responder` na lista de conversas em `app.js`

## 5. Testes

- [x] 5.1 Testes de auth: cookie com operador, sessão inválida sem operador, login com/sem operador selecionado
- [x] 5.2 Testes de mensagem: `sent_by` gravado no outbound, NULL quando sem operador
- [x] 5.3 Testes de listagem: `last_responder` retornado corretamente na lista de conversas
