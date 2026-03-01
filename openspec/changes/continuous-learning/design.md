## Context

O draft engine hoje gera 3 variações em paralelo com Haiku, usando os últimos 10 edit pairs cronológicos como few-shot. Não há interpretação do motivo das edições, não há busca por similaridade, e não há mecanismo para o operador cristalizar padrões em regras permanentes.

O operador corrige erros estratégicos repetidamente (ex: IA joga preço antes de qualificar) sem que o sistema generalize. O objetivo é criar um loop de aprendizado contínuo com três camadas: anotação automática, retrieval inteligente, e cristalização de regras via review humano.

Volume: 10-20 conversas/dia, operador único (Caio ou membro do time). Pool de edit pairs cresce ~300-600/mês.

## Goals / Non-Goals

**Goals:**
- Cada interação melhora drafts futuros de forma mensurável
- O aprendizado é sobre decisão estratégica (quando qualificar, quando precificar, quando recuar), não imitação de estilo textual
- O sistema é interpretável: o operador pode ver o que foi aprendido, contestar e corrigir
- Zero fricção no fluxo quente (rajada de conversas): nenhum passo extra durante a operação
- Review e cristalização de regras acontecem no tempo do operador, não do sistema

**Non-Goals:**
- Fine-tuning de modelo (volume insuficiente, complexidade desnecessária)
- Aprendizado multi-operador (escopo futuro)
- Personalização por cliente/lead (escopo futuro)
- Dashboard de métricas de aprendizado (escopo futuro)

## Decisions

### 1. Situation summary como unidade de retrieval (não a mensagem do cliente)

A mesma mensagem ("quanto custa?") tem significado estratégico completamente diferente no primeiro contato vs. depois de qualificação. Embedding da mensagem isolada perde esse contexto.

O sistema gera um situation summary (2-3 frases) via Haiku antes de gerar os drafts. Esse summary descreve a situação estratégica: estágio da conversa, perfil aparente do cliente, o que já foi discutido, qual o movimento esperado. O summary serve dois propósitos: (1) contexto explícito no prompt dos drafts, (2) chave de busca para retrieval futuro.

**Alternativa considerada**: Embedding da conversa inteira. Descartada porque conversas longas produzem embeddings difusos que perdem especificidade situacional.

### 2. ChromaDB como vector store local

Com pool de centenas a poucos milhares de edit pairs, um serviço externo (Pinecone, Qdrant) é overkill. SQLite com cosine similarity manual funciona mas exige gerenciar embeddings e serialização manualmente.

ChromaDB roda in-process, usa SQLite internamente (compatível com a stack), faz embedding + armazenamento + busca numa API. Suporta metadata filtering nativo (ex: buscar só entre pares validados).

O ChromaDB armazena situation summaries embedados com metadata (edit_pair_id, was_edited, validated, approach_selected). A fonte de verdade dos dados permanece no SQLite principal.

**Alternativa considerada**: sqlite-vec. Mais leve, mas API menos madura e sem metadata filtering nativo.

### 3. Anotação estratégica assíncrona sem fricção no fluxo quente

As conversas chegam em rajada (almoço, fim de expediente). Qualquer passo extra por mensagem no fluxo quente é inaceitável.

Após cada envio, um background task (asyncio.create_task) chama Haiku para analisar o diff entre draft selecionado e mensagem enviada. A anotação é salva no edit pair sem interação do operador. Se não houve edição, a anotação registra confirmação da abordagem.

### 4. Review como fluxo frio separado

A validação humana das anotações acontece em tela dedicada, acessível quando o operador quiser. Três ações possíveis: confirmar anotação (OK), rejeitar (Errado), ou promover a regra permanente. A tela prioriza casos com edição (onde o sistema potencialmente errou) e agrupa por padrão quando possível.

O sistema funciona sem review. Anotações não validadas são usadas como few-shot com peso implicitamente menor (validadas aparecem primeiro no retrieval via metadata filter). Quando o operador valida, a anotação ganha prioridade.

### 5. Regras como texto livre no system prompt

Regras promovidas são armazenadas como texto em tabela SQLite (learned_rules) e injetadas numa seção dedicada do system prompt. Formato: descrição da regra em linguagem natural. O operador pode editar o texto da regra ao promover, e pode desativar/reativar regras a qualquer momento.

**Alternativa considerada**: Regras estruturadas (condition → action). Descartada por rigidez excessiva; linguagem natural é mais flexível e o LLM interpreta bem.

### 6. Fluxo de geração sequencial: summary → retrieval → drafts

O fluxo passa de paralelo-direto para sequencial com etapa prévia:

```
Msg chega
  → Step 1: Gera situation summary (Haiku, ~300ms)
  → Step 2: Busca edit pairs similares no ChromaDB (< 50ms)
  → Step 3: Gera 3 drafts em paralelo (Haiku, ~500ms)
     Prompt inclui: system + regras + knowledge + summary + few-shot similares + conversa
  → Step 4 (background): Salva summary, após envio gera annotation
```

Latência adicional de ~300ms é negligenciável conforme validado com o operador.

## Risks / Trade-offs

**Qualidade da anotação automática** → A Camada 1 pode interpretar incorretamente o motivo de uma edição (ex: atribuir a tom o que foi correção estratégica). Mitigação: anotações não validadas nunca viram regras; o review humano filtra interpretações ruins; few-shot ruim sai do pool naturalmente por relevância.

**ChromaDB como dependência** → Adiciona complexidade ao setup e risco de incompatibilidade futura. Mitigação: os dados mestres ficam no SQLite; o ChromaDB é um índice reconstruível a qualquer momento a partir dos situation summaries no SQLite.

**Context window do prompt** → Com situation summary + few-shot enriquecido + regras + knowledge, o prompt pode crescer. Mitigação: limitar few-shot a 5 exemplos; usar Haiku (200K context) que tem janela ampla; monitorar via prompt logging existente.

**Cold start** → Sem edit pairs, não há retrieval nem anotações. Mitigação: fallback graceful para o comportamento atual (zero-shot com system prompt e knowledge base).
