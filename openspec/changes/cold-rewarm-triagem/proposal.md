## Why

Leads do curso CDO que entraram em `handbook_sent` ou `link_sent` há mais de 30 dias e não fecharam somam dois meses acumulados (~200 conversas). Dentro desse pool existe um subgrupo recuperável: quem não negou explicitamente, quem disse "mês que vem volto" (adiamento declarado, promessa ao próprio lead), quem silenciou após ver o preço (objeção de preço potencialmente tratável com mentoria). Rodar triagem 1:1 manualmente em 200 conversas é inviável pro operador. Objetivo: fazer o Haiku ler cada histórico, classificar a objeção de saída, aplicar uma matriz determinística de ação, compor mensagem pessoal no tom do Caio e apresentar tudo num modal de revisão 1x (botão manual), com disparo em batch respeitando rate limit e cap mensal de mentoria.

## What Changes

- Novo botão "Cold Rewarm" na UI (ao lado do "Reesquentar D-1") que dispara `POST /cold-rewarm/preview`.
- Pipeline de triagem em duas chamadas Haiku por candidato: (1) classificador de objeção + citação literal + confiança, (2) compositor de mensagem condicional à ação.
- Matriz determinística estágio × objeção → ação:

  |                         | preço     | timing   | conteúdo | tire-kicker | negativo |
  |-------------------------|-----------|----------|----------|-------------|----------|
  | link_sent               | mentoria  | mentoria | mentoria | skip        | skip     |
  | handbook_sent           | skip      | mentoria | conteudo | skip        | skip     |

  Quando `classification_confidence='low'`, força skip. Quando o cap mensal de mentoria está cheio, mentoria vira conteudo para link_sent e skip para handbook_sent.

- Priorização na seleção: link_sent + "mês que vem volto" no topo, depois link_sent com timing/preço, depois link_sent com conteúdo, depois handbook_sent com timing. Tire-kicker e negativo nunca são apresentados.
- Limite de preview = 20 candidatos por execução. Operador pode rodar de novo no dia seguinte pra próximos 20.
- Modal de revisão mostra: nome, telefone, estágio, classificação inferida, citação literal do lead (com data), ação recomendada, rascunho da mensagem editável. Operador pode remover itens e editar mensagem.
- Execução em batch com `next_delay()` existente (60s ± uniforme -20/+40 = janela 40-100s). Agenda em `scheduled_sends` como `created_by='cold_rewarm'`.
- Cap mensal de mentoria configurável via env `COLD_MENTORIA_MONTHLY_CAP` (default 15). Atingido o cap, o Haiku passa a receber instrução de não oferecer mentoria, só conteúdo.
- Cooldown: conversa que recebeu cold rewarm nos últimos 90 dias não volta ao pool (evita dupla queima no mesmo backlog).
- Tom do compositor: primeira pessoa (Caio), minúsculas, sem em-dash, pode incluir typo sutil ocasional (1 em cada 4-5), cita literalmente o trecho do lead com referência temporal ("você comentou em [data]...").

## Capabilities

### New Capabilities
- `cold-triage`: Dado o pool de leads cold (handbook/link +30d sem negativa explícita), classifica cada conversa (objeção + citação + confiança), aplica matriz determinística pra decidir ação, respeita cap mensal de mentoria, compõe mensagem no tom Caio, prioriza candidatos por força do sinal, limita a 20 por batch.

### Modified Capabilities
- `rewarm-agent` (existente): Nenhuma mudança. O fluxo D-1 continua independente. A diferença é que `cold_rewarm` tem prompt, matriz e UX próprios, não reusa `decide_rewarm_action`.

## Impact

- **Novo service** `app/services/cold_triage.py`: seleção, Haiku classificador, matriz, Haiku compositor, cap checker, run_preview.
- **Novo router** `app/routes/cold_rewarm.py`: `POST /cold-rewarm/preview`, `POST /cold-rewarm/execute`.
- **Migration** `cold_dispatches_table`: id, conversation_id, classification, confidence, quote_from_lead, action, message_sent, scheduled_send_id, status (previewed/approved/sent/skipped), responded_at, created_at.
- **Config** `cold_mentoria_monthly_cap: int = 15` em `app/config.py`.
- **Frontend**: modal novo (`cold-rewarm-modal`) que reusa CSS do rewarm existente. Novo módulo JS em `app/static/js/ui/cold_rewarm.js`.
- **Sem cron.** V1 é só botão. Automação entra em change separada quando os primeiros disparos validarem comportamento.
- **Sem downsell.** CDO é o único produto. Mentoria é a única oferta comercial no fluxo.
