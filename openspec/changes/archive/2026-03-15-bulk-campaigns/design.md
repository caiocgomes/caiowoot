## Context

O CaioWoot é um copiloto de vendas via WhatsApp com arquitetura simples: SQLite + aiosqlite, Evolution API para envio, asyncio para background tasks, WebSocket para real-time, e frontend vanilla JS. O time de marketing precisa de envio em massa para ~100 contatos por campanha, com evasão de detecção de spam da Meta.

O sistema já tem um padrão de poller (scheduler.py, 30s) para envios agendados. A integração com Evolution API (sendText, sendMedia) já existe e não precisa de mudanças.

## Goals / Non-Goals

**Goals:**
- Permitir criação de campanhas com upload de CSV e geração automática de variações
- Execução com randomização de conteúdo e timing para evitar detecção de spam
- Detecção automática de bloqueio e pausa da campanha
- Retomada de campanhas após bloqueio (continuar de onde parou)
- Dashboard de acompanhamento com status por contato
- Respostas de destinatários integradas ao fluxo conversacional existente

**Non-Goals:**
- Múltiplas linhas/números (o bloqueio da Meta é temporário, 24h, mesma linha)
- Push notifications (Web Push API) para alertar sobre campanhas
- A/B testing ou analytics de performance de variações
- Warm-up automático de linhas
- Envio de documentos/PDFs (apenas texto + imagem opcional)
- Importação de contatos de fontes externas (apenas CSV)

## Decisions

### 1. Poller com `next_send_at` para execução (não asyncio.sleep loop)

Cada campanha running tem um campo `next_send_at`. Um poller roda a cada 10s, encontra campanhas com `next_send_at <= now` e `status = running`, envia a próxima mensagem, sorteia nova variação e intervalo, e atualiza `next_send_at`.

**Alternativa descartada**: asyncio task de longa duração com sleep entre envios. Não sobrevive a restart do servidor e exige gerenciamento de lifecycle de tasks.

**Alternativa descartada**: Reaproveitar o scheduler.py existente (30s). O intervalo de 30s é grosseiro demais. Um poller dedicado de 10s dá precisão suficiente sem overhead significativo.

### 2. Variações geradas pelo Claude Haiku em batch

O operador escreve uma mensagem base. O sistema chama Claude Haiku uma vez pedindo 8 variações que difiram em estrutura, abertura, registro e comprimento. As variações são salvas em `campaign_variations` e o operador revisa antes de aprovar.

**Por que Haiku**: mesmo modelo já usado para drafts. Custo baixo (~$0.01 para 8 variações). Latência aceitável (~2-3s).

**Por que batch único**: gerar todas de uma vez permite instruir o Claude a maximizar diversidade entre elas. Gerar uma por vez não garante que sejam genuinamente diferentes.

### 3. Detecção de bloqueio por heurística de falhas consecutivas

Se 5 envios consecutivos falham, a campanha é pausada automaticamente com status `blocked`. Não há como distinguir com certeza bloqueio da Meta vs erro temporário da Evolution API, mas 5 falhas seguidas é um sinal forte o suficiente.

**Alternativa descartada**: Verificar status da conexão via API da Evolution antes de cada envio. Adiciona latência e a API pode reportar conectado enquanto a Meta já está throttling.

### 4. Imagem com recompressão aleatória

Se a campanha inclui imagem, o sistema aplica uma leve variação de qualidade JPEG (85-95%) a cada envio, gerando hashes diferentes. Isso evita detecção de mídia idêntica pela Meta sem alterar a imagem visualmente.

**Alternativa descartada**: Enviar imagem e texto separados. Parece mais natural mas dobra o número de chamadas à API e complica o retry.

### 5. Tagueamento de conversas via campo `origin_campaign_id`

Quando o webhook recebe uma resposta de um número que é contato de uma campanha, a conversa recebe `origin_campaign_id` no banco. Isso permite ao operador saber o contexto sem poluir a UI da campanha com status "replied".

**Lookup**: ao receber webhook, checar se o phone_number existe em `campaign_contacts` com `status = sent`. Se sim, popular `origin_campaign_id` na conversa.

### 6. Nova tab "Campanhas" no sidebar

Segue o padrão existente (Conversas, Conhecimento, Aprendizado). Sidebar lista campanhas, main area mostra detalhe. A criação de campanha usa o main area com um formulário multi-step (upload CSV → escrever mensagem → revisar variações → configurar timing → iniciar).

## Risks / Trade-offs

- **[Falso positivo no bloqueio]** → 5 falhas podem ser erro temporário de rede, não bloqueio. Mitigação: operador pode retomar manualmente. Melhor pausar por precaução.
- **[Qualidade das variações]** → Claude pode gerar variações semanticamente muito similares. Mitigação: prompt explícito pedindo diversidade de estrutura, tom e comprimento. Operador revisa antes de disparar.
- **[Poller de 10s no SQLite]** → Poll a cada 10s em SQLite com WAL é negligível em termos de IO. Para ~100 contatos por campanha, zero preocupação de performance.
- **[Imagem recompressão]** → Requer Pillow como dependência. Alternativa: enviar sem recompressão para 100 contatos (risco baixo). Decisão: implementar, custo mínimo.

## Open Questions

- Formato exato do CSV: apenas `telefone,nome` ou aceitar colunas extras para placeholders na mensagem (ex: `{{empresa}}`)?
- Limitar a 1 campanha running por vez (para não sobrecarregar a linha) ou permitir múltiplas simultâneas?
