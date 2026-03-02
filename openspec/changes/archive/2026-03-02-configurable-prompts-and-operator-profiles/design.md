## Context

O sistema CaioWoot gera drafts de resposta via Claude Haiku usando prompts hardcoded como constantes Python em 3 arquivos: `draft_engine.py` (SYSTEM_PROMPT + APPROACH_MODIFIERS), `situation_summary.py` (SUMMARY_PROMPT), `strategic_annotation.py` (ANNOTATION_PROMPT). Qualquer alteração exige editar código e reiniciar.

Operadores são apenas rótulos no cookie de sessão. O sistema sempre diz "Você é o Caio" independente de quem está logado, gerando respostas incorretas quando outro operador usa o sistema.

## Goals / Non-Goals

**Goals:**
- Permitir edição de prompts globais pela UI sem restart, persistidos no SQLite
- Decompor o SYSTEM_PROMPT monolítico em seções editáveis vs. infra fixa
- Cada operador pode manter um perfil com contexto livre injetado no prompt
- Controle de acesso: prompts globais só admin, perfil pessoal cada operador
- Leitura do banco a cada geração (sem cache, dado que é SQLite local)

**Non-Goals:**
- Versionamento/histórico de prompts (pode vir depois)
- Prompts diferentes por operador (os globais são compartilhados)
- Edição das partes de infra do prompt (JSON format, WhatsApp formatting, temporal context)
- Migração de dados existentes (seed com valores atuais hardcoded)

## Decisions

### 1. Decomposição do SYSTEM_PROMPT

O SYSTEM_PROMPT atual tem ~48 linhas misturando persona, tom, regras de venda, regras de formatação, e formato de resposta. Será decomposto em:

**Editáveis (vão pro banco):**
- `postura` — seção "## Postura" do prompt atual
- `tom` — seção "## Tom"
- `regras` — seção "## Regras"
- `approach_direta` — modifier da variação direta
- `approach_consultiva` — modifier da variação consultiva
- `approach_casual` — modifier da variação casual
- `summary_prompt` — SUMMARY_PROMPT inteiro
- `annotation_prompt` — ANNOTATION_PROMPT inteiro

**Fixos (ficam hardcoded):**
- Parágrafo de abertura ("Você é o {operator_name} respondendo mensagens...")
- Seção "## Formatação WhatsApp"
- Seção "## Contexto temporal"
- Seção "## Anexos"
- Seção "## Formato de resposta" (JSON)

O parágrafo de abertura passa a ser dinâmico: usa nome do operador + contexto do perfil.

**Alternativa descartada:** expor o prompt inteiro como um textarea gigante. Risco de o operador quebrar a formatação JSON ou WhatsApp, travando o sistema.

### 2. Tabela `prompt_config` (key-value)

```sql
CREATE TABLE IF NOT EXISTS prompt_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Key-value simples. Keys são as 8 seções editáveis. Na primeira execução (ou quando uma key não existe), o sistema usa os valores hardcoded atuais como fallback, sem precisar de seed/migration de dados.

**Alternativa descartada:** uma coluna por seção numa tabela de uma única row. Funciona, mas adicionar novas seções editáveis exigiria migration. Key-value é extensível sem schema change.

### 3. Tabela `operator_profiles`

```sql
CREATE TABLE IF NOT EXISTS operator_profiles (
    operator_name TEXT PRIMARY KEY,
    display_name TEXT,
    context TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

`operator_name` é o identificador do operador (mesmo valor que está no cookie/OPERATORS list). `context` é o textarea livre. `display_name` é opcional (se vazio, usa `operator_name`).

Perfil é criado on-demand: se o operador nunca editou seu perfil, o sistema gera prompt sem a seção de perfil (comportamento atual).

### 4. Montagem do prompt no draft_engine

O prompt final é montado assim:

```
[FIXO] Parágrafo de abertura com nome do operador + contexto do perfil
[BANCO] postura
[BANCO] tom
[BANCO] regras
[FIXO] Formatação WhatsApp
[FIXO] Contexto temporal
[FIXO] Anexos
[FIXO] Formato de resposta JSON
[BANCO] Regras aprendidas (já existente)
[BANCO] Estilo desta variação (approach modifier)
```

O perfil do operador entra no parágrafo de abertura:

```
Você é o João respondendo mensagens de clientes no WhatsApp sobre cursos de IA do Caio.

## Sobre quem está respondendo
{operator_profile.context}
```

Se não há perfil, cai no comportamento genérico atual.

### 5. Admin: env var ADMIN_OPERATOR

Nova env var `ADMIN_OPERATOR` com o nome do operador admin. A API de prompts globais verifica se o operador logado (do cookie) é o admin antes de permitir escrita. Se ADMIN_OPERATOR não está definida, o primeiro operador da lista OPERATORS é considerado admin.

**Alternativa descartada:** campo `is_admin` no perfil do operador. Requer que alguém defina no banco quem é admin, criando chicken-and-egg. Env var é simples e seguro.

### 6. API endpoints

```
GET  /api/settings/prompts          — lê todos os prompts (qualquer operador)
PUT  /api/settings/prompts          — atualiza prompts (só admin)
GET  /api/settings/profile          — lê perfil do operador logado
PUT  /api/settings/profile          — atualiza perfil do operador logado
GET  /api/settings/is-admin         — retorna se operador logado é admin
```

### 7. UI: modal ou página

Modal na interface principal, ativado por botão de engrenagem. Duas abas:
- **Prompts** (visível só pra admin): textareas para cada seção editável
- **Meu Perfil** (visível pra todos): nome de exibição + textarea de contexto

## Risks / Trade-offs

- **Prompt quebrado pelo admin** → O admin pode escrever um prompt que produz respostas ruins. Mitigação: os prompts têm fallback pros valores hardcoded, e o admin pode restaurar clicando "Restaurar padrão" em cada seção.
- **Perfil vazio não muda comportamento** → Se operador não preenche perfil, o sistema funciona como hoje. Isso é feature, não bug.
- **Sem validação de conteúdo** → Não há como validar se o prompt escrito faz sentido. Confiamos no admin.
- **Latência zero de leitura** → SQLite local, sem cache necessário. Se migrar pra banco remoto no futuro, precisaria de cache.
