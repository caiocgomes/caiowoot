## Why

O sistema hoje usa os últimos 10 edit pairs em ordem cronológica como few-shot no prompt, sem matching semântico, sem filtro de qualidade, sem interpretação do motivo das edições. Isso é o nível zero de aprendizado. O operador corrige o mesmo tipo de erro repetidamente (ex: IA joga preço antes de qualificar) e o sistema não generaliza a correção.

O objetivo é criar um loop de aprendizado contínuo onde cada interação (draft gerado → edição do operador → mensagem enviada) alimenta drafts futuros de forma inteligente, capturando não o estilo do texto mas a decisão estratégica por trás de cada correção.

## What Changes

- Antes de gerar drafts, o sistema produz um **situation summary** (2-3 frases descrevendo a situação estratégica da conversa) via chamada Haiku
- O situation summary entra no prompt dos 3 drafts como contexto explícito e é salvo junto ao edit pair para retrieval futuro
- Após o envio de cada mensagem, um job background gera uma **strategic annotation** que interpreta o diff entre draft e mensagem enviada (ou confirma a abordagem se não houve edição)
- O retrieval de few-shot passa de "últimos 10 cronológicos" para **busca por similaridade de situation summary** usando ChromaDB como vector store local
- Nova tela de **review** (fluxo frio) onde o operador pode revisar anotações estratégicas e promover as que representam padrões recorrentes a **regras permanentes** que entram no system prompt
- Regras promovidas são armazenadas e injetadas automaticamente no system prompt de todos os drafts futuros

## Capabilities

### New Capabilities
- `situation-summary`: Geração de resumo estratégico da conversa antes dos drafts, usado como contexto no prompt e como chave de retrieval
- `strategic-annotation`: Análise assíncrona pós-envio que interpreta o motivo das edições do operador e gera anotações estruturadas
- `smart-retrieval`: Busca vetorial por situações similares usando ChromaDB, substituindo o retrieval cronológico atual
- `learning-review`: Tela de review para o operador validar anotações e promover regras permanentes
- `learned-rules`: Armazenamento e injeção de regras cristalizadas no system prompt

### Modified Capabilities
- `draft-engine`: Prompt passa a incluir situation summary, few-shot via retrieval inteligente, e regras aprendidas
- `prompt-logging`: Edit pairs expandidos com situation_summary e strategic_annotation

## Impact

- **app/services/draft_engine.py**: Refatoração do fluxo de geração (summary → retrieval → drafts)
- **app/models.py**: Novos campos em EditPair (situation_summary, strategic_annotation, validated)
- **app/database.py**: Migração do schema SQLite para novos campos + tabela de regras
- **Dependência nova**: `chromadb` no pyproject.toml
- **Nova rota API**: endpoints para review de anotações, promoção de regras, listagem de regras ativas
- **Frontend**: Nova tela de review (pode ser implementada depois do backend)
