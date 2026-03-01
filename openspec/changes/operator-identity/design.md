## Context

CaioWoot é usado por múltiplos operadores simultaneamente, especialmente durante lançamentos. O sistema hoje tem autenticação por senha compartilhada sem distinção de quem está operando. Não há rastreamento de autoria nas mensagens enviadas.

O auth atual usa `itsdangerous` com cookie assinado contendo `{"authenticated": True}`. Não existe conceito de identidade de operador.

## Goals / Non-Goals

**Goals:**
- Saber quem enviou cada mensagem outbound
- Visualizar na lista de conversas quem respondeu por último
- Configuração simples de operadores via variável de ambiente

**Non-Goals:**
- Sistema de usuários com cadastro, permissões ou roles
- Trocar de operador sem deslogar (cada pessoa usa sua própria máquina)
- Influenciar a geração de drafts pela IA com base no operador
- Claim/lock de conversas

## Decisions

### Lista de operadores via variável de ambiente
Os nomes dos operadores ficam em `OPERATORS` como string separada por vírgula (ex: `OPERATORS=Caio,João,Maria`). Sem banco, sem CRUD, sem tela de admin.

**Alternativa considerada**: tabela de operadores no SQLite. Rejeitada porque adiciona complexidade desnecessária para uma lista que muda raramente. Editar uma env var e reiniciar é suficiente.

### Seleção de nome na tela de login
Após digitar a senha correta, o operador seleciona seu nome na mesma tela (ou numa etapa imediata). O nome vai para o payload do cookie de sessão: `{"authenticated": True, "operator": "Caio"}`.

**Alternativa considerada**: tela separada pós-login. Rejeitada porque adiciona um redirect extra sem ganho. O login já é uma tela simples, um select a mais não polui.

### Coluna `sent_by` na tabela messages
Nova coluna `sent_by TEXT` na tabela `messages`. Preenchida apenas para mensagens outbound. Mensagens inbound e mensagens históricas anteriores à mudança ficam com `NULL`.

**Alternativa considerada**: tabela separada de autoria. Rejeitada porque é uma coluna simples numa tabela existente, sem necessidade de normalização.

### Exibição na lista de conversas
O backend calcula quem respondeu por último ao montar a lista de conversas (subquery no último outbound de cada conversa). O frontend exibe o nome abaixo do preview da última mensagem.

**Alternativa considerada**: campo `last_responder` na tabela `conversations` atualizado a cada envio. Rejeitada porque cria duplicação de estado. A query é simples o suficiente para calcular on-the-fly dado o volume de conversas do sistema.

## Risks / Trade-offs

- **Operador não configurado na env**: se alguém esquece de adicionar um nome na lista `OPERATORS`, essa pessoa não consegue logar. Mitigação: validação clara na tela de login (a lista aparece visivelmente).
- **Cookie existente sem operador**: sessões criadas antes dessa mudança não terão o campo `operator`. Mitigação: middleware verifica a presença do campo e redireciona para login se ausente, forçando nova autenticação.
- **Performance da subquery**: para cada conversa na lista, precisa buscar o último outbound. Mitigação: o volume de conversas ativas é baixo (dezenas), a query com subquery correlacionada é trivial para SQLite.
