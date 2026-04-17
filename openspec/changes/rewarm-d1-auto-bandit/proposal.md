## Why

O rewarm D-1 existente depende do operador apertar o botão "Reesquentar D-1" todo dia. Já rodou manualmente por dois dias com resultado ok. Próximo passo: tirar o operador do loop diário e, no mesmo movimento, aprender qual janela do dia (almoço ou fim de expediente) converte mais respostas produtivas por lead, de forma contextual e continuamente adaptativa. Volume atual é baixo (~10 leads/dia), o que define todas as escolhas de design.

## What Changes

- Pipeline diário automático: um cron matinal (10:30 America/Sao_Paulo) seleciona candidatos D-1, decide braço de envio por lead, e enfileira um único toque em `scheduled_sends` com `send_at` na janela sorteada (12:30 ou 18:30 ± jitter 15 min).
- Alocação contextual via Thompson sampling com regressão logística bayesiana por braço (Laplace approximation). Cada lead é alocado ao braço com maior probabilidade amostrada de resposta produtiva, condicional a features do lead.
- Warmup de 40 dispatches antes do Thompson ligar: nessa fase, alocação é uniforme 50/50 para popular o posterior com base mínima.
- Reward binário `produtiva` via classificação Haiku ao chegar inbound dentro de 48h do envio. Resposta não-produtiva (rejeição, hostilidade, "ok obrigado") ou ausência de resposta em 48h contam como reward 0. Classificação roda como task em background no webhook.
- Dois braços somente (`noon`, `evening`). Janelas fixas 12:30 e 18:30 com jitter de ±15 min por lead para desconcentrar o envio.
- Features iniciais: (1) hora típica de resposta histórica do lead (mediana, fallback `unknown`); (2) estágio do funil (`handbook_sent` vs `link_sent`).
- Cron noturno (02:00) fecha dispatches com mais de 48h sem resposta (reward=0) e refita posterior bayesiano de cada braço do zero em cima do histórico fechado. Sem estado online incremental — refit é trivial no volume previsto.
- Conversão em 30d NÃO entra na reward, mas é gravada em paralelo em `rewarm_dispatches.converted_at` via hook de funnel para diagnóstico de Goodhart (resposta produtiva correlaciona com compra?).
- Webhook já cancela `scheduled_sends` pendentes quando lead responde antes do envio; esse path não gera reward (toque nunca saiu), e o dispatch associado é marcado `skipped_client_replied`.
- Flag existente `rewarm_auto_send` passa a controlar o cron matinal: off = no-op, on = dispatch automático. Mantém retrocompatibilidade com o endpoint manual.

## Capabilities

### New Capabilities
- `rewarm-bandit`: Bandit contextual que decide, por lead e por dia, qual janela de envio (noon/evening) maximiza a probabilidade de resposta produtiva. Thompson sampling sobre regressão logística bayesiana Laplace por braço, refit diário em cima do histórico fechado. Warmup determinístico nos primeiros 40 dispatches.
- `rewarm-cron`: Lifespan tasks que rodam o pipeline matinal de dispatch e o pipeline noturno de closeout + refit, com persistência de "já rodei este slot hoje" via tabela `cron_runs` para sobreviver reinício de container.
- `rewarm-reward`: Hook webhook que, ao receber inbound de conversa com dispatch aberto, chama Haiku classificando a resposta como produtiva ou não-produtiva e grava reward no dispatch.

### Modified Capabilities
- `rewarm-agent` (existente): a decisão de conteúdo (message vs skip) segue via `decide_rewarm_action`. O que muda é que ela passa a ser chamada pelo cron, em horário específico por braço, e o resultado é gravado em `scheduled_sends` + `rewarm_dispatches` ao invés de ser enviado direto.
- `scheduler` (existente): ao marcar `scheduled_send` como enviado, atualiza `rewarm_dispatches.sent_at` se o send tiver `created_by='rewarm_agent'` e `rewarm_dispatch_id` associado.

## Impact

- **Novo service** `app/services/rewarm_bandit.py`: feature extraction, sampler Thompson logístico, classificador de resposta, refit Laplace.
- **Novo service** `app/services/rewarm_cron.py`: loops matinal e noturno, persistência de slots.
- **Migrations**: `rewarm_dispatches`, `bandit_state`, `cron_runs`.
- **Modificações**: `app/main.py` (adiciona task), `app/services/scheduler.py` (hook de sent_at no dispatch), `app/routes/webhook.py` (task de reward).
- **Dependências novas**: `numpy`, `scipy` (já presentes indiretamente por chromadb, mas declara explicitamente).
- **Sem mudança de frontend**: endpoint manual continua funcional; cron roda independente.
- **Goodhart guard**: grava `converted_at` em dispatch se o funnel avançar em 30 dias — apenas observacional nesta versão, sem efeito no bandit. Permite análise offline posterior.
- **Volume e timeline**: com 10 leads/dia, os 40 dispatches de warmup levam ~4 dias. Sinal estatístico razoável em 6-8 semanas se efeito for grande; pode nunca discriminar se efeito for pequeno (~2-3 pp de diferença) — limitação inerente do volume.
