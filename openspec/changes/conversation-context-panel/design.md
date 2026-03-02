## Context

O operador gerencia dezenas de conversas simultâneas e perde contexto ao voltar a um lead. O `situation_summary` já existe como texto livre gerado a cada draft, mas é transitório e não estruturado. Não há como saber rapidamente qual produto o lead quer ou em que etapa do funil está sem reler a conversa.

## Goals / Non-Goals

**Goals:**
- Rastreamento persistente de produto de interesse e etapa do funil por conversa
- Atualização automática via IA (copilot) a cada geração de drafts
- Correção manual pelo operador com um clique
- Painel lateral direito no desktop exibindo contexto estruturado + resumo
- Dados estruturados no banco para queries futuras (ex: "todos com link enviado")

**Non-Goals:**
- Múltiplos produtos por conversa (futuro, se necessário)
- Funil por operador (global por conversa)
- Dashboard/relatórios de funil (apenas dados no banco por enquanto)
- Painel no mobile (escondido, sem espaço)
- Filtro de conversas por etapa na sidebar (futuro)

## Decisions

### 1. Colunas `funnel_product` e `funnel_stage` na tabela `conversations`

Adicionar `funnel_product TEXT` e `funnel_stage TEXT` na tabela `conversations`. Ambos nullable (conversa nova = sem classificação).

Valores de `funnel_stage` como TEXT livre mas com enum no código: `qualifying`, `decided`, `handbook_sent`, `link_sent`, `purchased`.

Valores de `funnel_product` como TEXT livre (nomes dos cursos). Lista dos produtos conhecidos vem dos nomes dos arquivos em `knowledge/*.md` filtrados por prefixo `curso-`, mapeados para labels legíveis. Permite valor livre caso surja produto novo.

Alternativa descartada: tabela separada `conversation_funnel`. Overengineering para um produto + uma etapa por conversa.

### 2. Extração estruturada no situation_summary

Estender `generate_situation_summary()` para retornar JSON com três campos: `summary` (texto livre, como hoje), `product` (string ou null), `stage` (enum ou null).

O prompt do Haiku muda para pedir resposta em JSON. A função retorna um dict em vez de string. O draft_engine consome o `summary` como antes e adicionalmente salva `product`/`stage` na conversa.

Se o parse do JSON falhar (Haiku respondeu texto livre), usa a resposta inteira como summary e ignora product/stage. Graceful degradation.

### 3. Atualização automática no fluxo de geração de drafts

No `_build_prompt_parts()`, após gerar o situation_summary estruturado, faz UPDATE na conversa se product ou stage mudaram. Isso acontece naturalmente a cada mensagem inbound (que dispara draft generation).

O operador não precisa fazer nada. A IA mantém o funil atualizado. Se errar, operador corrige via painel.

### 4. Endpoint PATCH para correção manual

`PATCH /conversations/{id}/funnel` com body `{ "funnel_product": "...", "funnel_stage": "..." }`. Campos opcionais, atualiza só o que veio.

Não usa PUT porque é atualização parcial. Não conflita com o GET que já existe.

### 5. Painel lateral direito (desktop only)

Div `#context-panel` dentro de `#main`, ao lado do chat. Aparece quando uma conversa está aberta. Largura fixa ~280px. Contém:

- Dropdown de produto (editável)
- Radio buttons ou stepper para etapa do funil
- Bloco de texto com situation_summary mais recente (read-only)

Escondido no mobile (media query). Sem toggle por enquanto (sempre visível no desktop quando tem conversa aberta).

### 6. Dados do funil na API

`GET /conversations` retorna `funnel_product` e `funnel_stage` em cada item da lista.
`GET /conversations/{id}` retorna os mesmos campos no objeto `conversation`, mais o `situation_summary` mais recente (do último draft gerado).

O situation_summary no GET detail vem da tabela `drafts` (último draft da conversa), não de uma coluna nova na conversa.

## Risks / Trade-offs

- [IA pode classificar errado] → Operador corrige manualmente. Com o tempo, os few-shot examples melhoram a classificação.
- [JSON parse pode falhar] → Graceful degradation: usa texto como summary, ignora product/stage. Log do erro.
- [280px a menos no chat] → Mensagens já têm max-width 70%, funciona na maioria dos monitores. Em telas pequenas o painel pode comprimir, mas mobile está fora de escopo.
- [Etapas hardcoded] → TEXT no banco permite mudar sem migration. Enum só no código (fácil de alterar).
