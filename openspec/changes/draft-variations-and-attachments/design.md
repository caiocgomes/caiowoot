## Context

CaioWoot v1 está rodando: webhook recebe mensagens, gera 1 draft com Sonnet, operador edita e envia. Esta mudança expande o sistema para 3 variações com Haiku, adiciona controle do operador (instrução + regeneração), suporte a anexos, e logging de prompts para tuning futuro.

## Goals / Non-Goals

**Goals:**
- Dar ao operador 3 opções de resposta com abordagens diferentes
- Permitir controle sobre o tom/direção via barra de instrução
- Suporte a envio de imagens e documentos via WhatsApp
- Registrar dados suficientes para tuning futuro do modelo (prompt completo, todas as variações, qual foi escolhida, edições)
- Textarea maior para conforto de leitura/edição

**Non-Goals:**
- Sugestão automática de anexos pela IA
- Recebimento de mídia inbound (apenas envio outbound)
- Fine-tuning automatizado (apenas coleta de dados)
- Análise/dashboard sobre os dados de tuning

## Decisions

### D1: Haiku para variações, 3 chamadas em paralelo

Cada mensagem recebida dispara 3 chamadas ao Haiku via `asyncio.gather`. Cada chamada recebe o mesmo prompt base mas com um modificador de abordagem diferente:
- Variação A: "responda de forma direta e objetiva"
- Variação B: "responda de forma consultiva, fazendo perguntas de qualificação"
- Variação C: "responda de forma mais casual e acolhedora"

Haiku é ~10x mais barato e ~3x mais rápido que Sonnet. 3 chamadas Haiku em paralelo custam ~30% de 1 chamada Sonnet e completam em tempo similar.

**Alternativas consideradas:**
- 3 chamadas Sonnet: custo 3x maior, latência 3x maior. Desproporcional para variações
- 1 chamada com "gere 3 opções": modelos tendem a gerar variações superficiais quando pedem N opções numa só chamada. Chamadas separadas com instruções diferentes produzem respostas mais distintas
- Temperature sampling (mesma chamada, temperature alta): variações são aleatórias, não direcionadas

### D2: Modelo Haiku configurável via settings

Adicionar `CLAUDE_HAIKU_MODEL` ao .env/config com default `claude-haiku-4-5-20251001`. Manter `CLAUDE_MODEL` (Sonnet) para outros usos futuros se necessário.

### D3: Novo endpoint POST /conversations/{id}/regenerate

Endpoint para regenerar drafts. Aceita JSON:
```json
{
  "draft_index": null,          // null = regenerar todas, 0/1/2 = regenerar uma específica
  "operator_instruction": "...", // instrução opcional do operador
  "trigger_message_id": 123      // mensagem que originou os drafts
}
```

Dispara geração como background task (asyncio.create_task), igual ao fluxo atual. O frontend recebe os novos drafts via WebSocket.

### D4: Prompt logging em disco com hash SHA-256

O prompt completo (system + knowledge + few-shot + history + instrução do operador) é serializado como texto, hashado com SHA-256, e salvo em `data/prompts/{hash}.txt`. O hash é armazenado na tabela de drafts.

Se o hash já existe no disco, o arquivo não é reescrito (mesmo prompt = mesmo hash). Isso evita duplicação quando o operador regenera sem mudar nada.

Tamanho estimado: cada prompt ~5-10KB. Com 100 conversas/dia e 3 regenerações médias, ~300 arquivos/dia = ~1.5-3MB/dia. Trivial.

### D5: Drafts agrupados por grupo de geração

A tabela `drafts` ganha um campo `draft_group_id` (UUID) que agrupa as 3 variações de uma mesma geração. Isso permite:
- Buscar todas as variações de um grupo
- Substituir variações individuais ao regenerar
- Referenciar no edit_pair qual grupo e qual índice foi selecionado

### D6: Anexos via base64 na Evolution API

A Evolution API aceita mídia como base64 nos endpoints:
- `POST /message/sendMedia/{instance}` para imagens (com caption)
- `POST /message/sendDocument/{instance}` para PDFs/documentos

O frontend envia o arquivo como multipart/form-data. O backend lê o arquivo, converte para base64, e chama o endpoint apropriado baseado no MIME type:
- `image/*` → sendMedia
- Qualquer outro → sendDocument

Arquivos são salvos em `data/attachments/{message_id}_{filename}` para referência.

### D7: Textarea com min-height de 5 linhas

CSS simples: `min-height: 120px` no textarea (equivalente a ~5 linhas de texto). Cresce automaticamente com conteúdo via JS (auto-resize com scrollHeight).

## Schema Changes

```sql
-- Modificar tabela drafts
ALTER TABLE drafts ADD COLUMN draft_group_id TEXT;        -- UUID agrupando 3 variações
ALTER TABLE drafts ADD COLUMN variation_index INTEGER;     -- 0, 1, 2
ALTER TABLE drafts ADD COLUMN approach TEXT;               -- "direta", "consultiva", "casual"
ALTER TABLE drafts ADD COLUMN prompt_hash TEXT;            -- SHA-256 do prompt usado
ALTER TABLE drafts ADD COLUMN operator_instruction TEXT;   -- instrução do operador (se houver)

-- Modificar tabela edit_pairs
ALTER TABLE edit_pairs ADD COLUMN operator_instruction TEXT;
ALTER TABLE edit_pairs ADD COLUMN all_drafts_json TEXT;     -- JSON com as 3 variações
ALTER TABLE edit_pairs ADD COLUMN selected_draft_index INTEGER;
ALTER TABLE edit_pairs ADD COLUMN prompt_hash TEXT;
ALTER TABLE edit_pairs ADD COLUMN regeneration_count INTEGER DEFAULT 0;

-- Modificar tabela messages
ALTER TABLE messages ADD COLUMN media_url TEXT;
ALTER TABLE messages ADD COLUMN media_type TEXT;            -- "image", "document", null
```

## Nova Estrutura de Arquivos

```
caiowoot/
├── data/
│   ├── prompts/               # Prompt logs por hash
│   │   └── {sha256}.txt
│   └── attachments/           # Arquivos enviados
│       └── {msg_id}_{filename}
```

## Risks / Trade-offs

**[3 chamadas Haiku vs 1 Sonnet] → Melhor custo, qualidade aceitável**
Haiku é menos nuanced que Sonnet em vendas consultivas. Mitigation: o few-shot e o system prompt carregam a qualidade. Haiku segue instruções bem. Se a qualidade cair visivelmente, pode voltar para 1 Sonnet facilmente (só mudar config).

**[Prompt logging em disco] → Sem limpeza automática**
Os arquivos de prompt vão acumular ao longo do tempo. Para o volume atual (dezenas/dia), irrelevante por meses. Adicionar script de cleanup quando necessário.

**[Base64 para anexos] → Limite de tamanho**
Arquivos grandes em base64 ocupam ~33% mais memória. Para PDFs de curso (~1-5MB) e imagens (~0.5-3MB), é aceitável. Não suportar vídeos ou arquivos >10MB.

**[Sem validação de tipo de arquivo] → Risco baixo**
O operador é confiável (é o Caio). Não precisa de validação rigorosa de tipo de arquivo na v1. Validar apenas por MIME type para rotear para o endpoint correto da Evolution API.
