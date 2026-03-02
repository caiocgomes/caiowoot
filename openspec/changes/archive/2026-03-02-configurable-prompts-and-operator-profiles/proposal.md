## Why

Os prompts do sistema estão hardcoded no código Python. Qualquer ajuste de tom, postura ou regras de venda exige editar código e reiniciar o servidor. Operadores diferentes (Caio, João, Vitória) usam o mesmo prompt genérico que diz "Você é o Caio", independente de quem está logado. A IA não tem contexto sobre quem está respondendo, o que gera respostas incorretas (ex: João agradecendo quando alguém diz ser fã do Caio).

## What Changes

- UI de configuração acessível por botão na interface principal
- Prompts globais (postura, tom, regras de venda, approach modifiers, prompt de resumo, prompt de anotação) editáveis pela UI, persistidos no SQLite, lidos a cada geração de draft
- Partes de infraestrutura do prompt (formato JSON de resposta, formatação WhatsApp, contexto temporal) permanecem hardcoded e invisíveis na UI
- Perfil do operador com campo de contexto livre, editável por cada operador, injetado no prompt na hora da geração
- Aba de prompts globais restrita ao admin; aba de perfil acessível a cada operador
- Conceito de admin (flag simples, ex: env var `ADMIN_OPERATOR` ou primeiro da lista OPERATORS)

## Capabilities

### New Capabilities
- `prompt-config`: Persistência e edição de prompts globais decompostos (postura, tom, regras, approaches, summary prompt, annotation prompt). CRUD via API, UI com textareas, leitura pelo draft engine a cada geração
- `operator-profile`: Perfil por operador com nome de exibição e contexto livre para a IA. Cada operador edita o seu. Injetado como seção no system prompt na montagem do draft
- `settings-ui`: Tela de configuração com abas (Prompts para admin, Meu Perfil para todos). Acessível por botão na interface principal

### Modified Capabilities
- `draft-engine`: Leitura de prompts do banco em vez de constantes Python. Injeção do perfil do operador como seção do system prompt. Montagem do prompt final compondo partes fixas (infra) + editáveis (banco) + perfil do operador logado

## Impact

- **Backend**: nova tabela `prompt_config` no SQLite, nova tabela `operator_profiles`, novas rotas de API para CRUD de prompts e perfis, refactor do `draft_engine.py` para ler prompts do banco
- **Frontend**: nova tela de configuração (settings.html ou modal), botão de acesso na UI principal, lógica de abas com controle de permissão
- **Auth**: novo conceito de admin para proteger aba de prompts globais
- **Services**: `situation_summary.py` e `strategic_annotation.py` passam a ler seus prompts do banco em vez de constantes
