## Why

Durante lançamentos, vários operadores respondem conversas simultaneamente. Hoje não há como saber quem respondeu cada conversa, o que gera retrabalho e falta de visibilidade sobre quem está cuidando de quê.

## What Changes

- Após login com senha, operador seleciona seu nome de uma lista configurável via variável de ambiente
- Nome do operador fica gravado no cookie de sessão
- Mensagens outbound registram quem enviou (coluna `sent_by` em `messages`)
- Lista de conversas mostra o nome de quem respondeu por último em cada conversa

## Capabilities

### New Capabilities
- `operator-identity`: Identificação do operador na sessão e rastreamento de autoria nas mensagens enviadas. Cobre a seleção de nome pós-login, persistência no cookie, gravação no banco e exibição na lista de conversas.

### Modified Capabilities
- `password-gate`: Cookie de sessão passa a incluir o nome do operador além do flag de autenticação. Fluxo de login ganha etapa de seleção de nome.
- `message-sender`: Mensagens outbound passam a gravar `sent_by` com o nome do operador.
- `inbox-ui`: Lista de conversas passa a exibir o nome de quem respondeu por último.

## Impact

- **Backend**: `auth.py` (cookie payload, novo endpoint ou parâmetro no login), `database.py` (migration para `sent_by`), `routes/messages.py` (gravar `sent_by`), `routes/conversations.py` (retornar `sent_by` do último outbound)
- **Frontend**: `login.html` (tela de seleção de nome), `app.js` (exibir tag na lista de conversas)
- **Config**: Nova variável de ambiente `OPERATORS` (lista de nomes separados por vírgula)
- **Banco**: Migration adicionando coluna `sent_by TEXT` na tabela `messages`
