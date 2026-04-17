## Context

O `rewarm_engine.py` atual tem três responsabilidades claramente separáveis: (1) seleção de candidatos D-1, (2) decisão de conteúdo via Haiku, (3) envio com rate limit. Para automatizar sem reescrever, o novo pipeline reusa (1) e (2) integralmente, e substitui (3) por um agendamento em `scheduled_sends` controlado pelo bandit, que decide somente **quando** enviar, não **o que** enviar.

Essa separação é importante: a política de timing (bandit) pode evoluir sem tocar no prompt do agente de conteúdo, e o agente de conteúdo pode evoluir sem invalidar o estado do bandit (features são do lead, não da mensagem).

## Decisões-chave

### D1. Bandit contextual sobre não-contextual

Apesar do volume baixo (10/dia) tornar o ganho marginal do contextual pequeno nas primeiras semanas, a heurística de que **hora típica de resposta histórica** é preditiva de janela ideal é forte o suficiente para justificar o custo marginal de 2 features. Bandit não-contextual trataria corporate e autônomo igual, o que é manifestamente errado para o problema em mãos.

Trade-off aceito: posterior é largo por mais tempo (~6-8 semanas antes de discriminação estatística), alocação flutua, decisões parecem quase aleatórias no início. É comportamento correto e previsto, não bug.

### D2. Thompson logístico com Laplace, não UCB ou ε-greedy

- Thompson sampling é bem-estudado em bandit contextual com reward binário (Chapelle & Li 2011) e tem melhor regret empírico que ε-greedy na maioria dos regimes.
- LinUCB assume reward linear; resposta produtiva é binária e sigmoide descreve bem.
- Laplace approximation é suficiente para o volume: refit em batch no cron noturno resolve em centenas de ms.
- Sem floor de exploração explícito: Thompson explora naturalmente via ruído do sample. Se em 3-4 semanas a alocação virar 95/5 sem justificativa, adicionamos floor de 5% uniforme depois.

### D3. Refit do zero a cada noite, sem online learning

Com volume total esperado de ~3.000 dispatches em um ano, refit full é trivialmente rápido. Estado online (Kalman-like updates) introduz bugs sutis e dificulta debug. Princípio: estado derivável é melhor que estado incremental.

### D4. Warmup de 40 dispatches

Motivação: Thompson com posterior uniforme ainda é operacionalmente aleatório, mas não garante balanceamento amostral entre braços. Warmup determinístico 50/50 garante que cada braço começa com ~20 obs, suficiente para que o primeiro Laplace tenha curvatura real. Abaixo disso, a posterior degenera.

40 é ~4 dias de coleta no volume atual. Aceitável.

### D5. Reward 48h + classificação binária produtiva

- 48h pega respostas noturnas do mesmo dia e respostas da manhã seguinte. 24h perderia o segundo caso.
- Binário produtiva vs não-produtiva é mais limpo que tri-valorado (produtiva/neutra/tóxica). Neutras ("ok", "vou ver") são ambíguas; tratá-las como 0 é decisão de produto: se o toque gerou só uma resposta passiva, o objetivo não foi atingido.
- Classificação via Haiku: custo marginal ~3-5 chamadas/dia, negligenciável. Prompt separado do de conteúdo.

### D6. Conversão como observacional, não reward

Grava `converted_at` no dispatch se `funnel_stage` avançar para estado terminal (compra) dentro de 30 dias. Não entra no bandit. Serve para análise periódica: se respostas produtivas sobem mas conversão não, é sinal de Goodhart e a reward precisa mudar. Decisão explicitamente deferida para os próximos meses.

### D7. Integração com `scheduled_sends` existente

Em vez de criar nova fila, o bandit enfileira em `scheduled_sends` com `created_by='rewarm_agent'` e ganha de graça:
- Cancelamento automático se lead responder antes do envio (webhook já faz isso).
- Retry em caso de falha de envio (scheduler já reverte para pending).
- Dedup de 5s contra envio duplicado (send_executor).
- UI existente que mostra envios agendados.

Custo: `rewarm_dispatches.scheduled_send_id` como foreign key. Cross-check necessário entre as duas tabelas ao fechar dispatch, mas é uma query trivial.

### D8. Persistência de "slot rodado" via tabela, não memória

Container pode reiniciar. Tabela `cron_runs(slot_key, ran_at)` com UNIQUE em `(slot_key, DATE(ran_at))`. Antes de rodar, checa presença da linha do dia; depois, insere. Sobrevive restart, é auditável.

## Arquitetura de execução

```
06:00 UTC (~03:00 BRT):
  sem atividade relevante

10:30 BRT (cron matinal):
  rewarm_cron.daily_dispatch():
    se não rewarm_auto_send: return
    se cron_runs tem entrada pra slot="morning" hoje: return
    candidates = rewarm_engine.select_rewarm_candidates()
    para cada cand:
      features = rewarm_bandit.extract_features(cand.id)
      decision = rewarm_engine.decide_rewarm_action(cand.id)
      se decision.action == "skip":
        continue  # nem cria dispatch; agente foi explícito
      arm = rewarm_bandit.sample_arm(features)
      send_at = compute_slot(arm) + jitter(±15min)
      scheduled_send_id = insert scheduled_sends(
        content=decision.message,
        send_at=send_at,
        created_by='rewarm_agent'
      )
      insert rewarm_dispatches(
        conversation_id=cand.id,
        features_json=features,
        arm=arm,
        scheduled_send_id=scheduled_send_id,
        scheduled_for=send_at
      )
    insert cron_runs(slot_key='morning', ran_at=now)

12:30 BRT e 18:30 BRT (scheduler_loop já existente):
  para cada scheduled_send due:
    execute_send()
    se created_by='rewarm_agent':
      update rewarm_dispatches.sent_at
    marca scheduled_send como sent

[durante o dia, em qualquer momento] webhook inbound:
  processa mensagem como hoje
  se tem rewarm_dispatches com sent_at != null e responded_at == null
    e sent_at > now-48h:
      dispara task classify_and_reward()
        classifica produtiva via Haiku
        update dispatch (responded_at, productive, reward, closed_at)

02:00 BRT (cron noturno):
  rewarm_cron.nightly_closeout():
    se cron_runs tem entrada pra slot="nightly" hoje: return
    close_stale_dispatches()  # sent_at+48h < now e responded_at nulo → reward=0
    rewarm_bandit.refit_posterior()  # recalcula mu/sigma de cada braço
    insert cron_runs(slot_key='nightly', ran_at=now)
```

## Feature engineering

Duas features no vetor `x`:

1. **hora_resp_tipica**: mediana (em horas decimais, ex: 14.5) dos `created_at` das mensagens inbound anteriores dessa conversa. Se não há histórico inbound, valor é null → encoding como two dummies: `has_history=0`, `hora_resp_tipica=0`. Senão `has_history=1`, valor numérico.

2. **estagio**: `handbook_sent` vs `link_sent`. Binário.

Vetor final `x = [1 (intercept), has_history, hora_resp_tipica, estagio_link]`. Dimensão 4.

Pode parecer excessivo para só 2 features lógicas, mas encoding explícito evita problemas sutis com missing data.

## Modelo bayesiano

Por braço `a ∈ {noon, evening}`:
- Prior: `w_a ~ N(0, sigma_prior^2 I)` com `sigma_prior = 3.0` (fracamente informativo para logit).
- Likelihood: `y | w_a, x ~ Bernoulli(sigmoid(w_a^T x))` para dispatches fechados com `arm == a`.
- Posterior: aproximado por Laplace em torno do MAP.
  - MAP via Newton-Raphson (scipy.optimize.minimize com método Newton-CG, poucas iterações).
  - Covariância: `Sigma = H^{-1}` onde `H` é a hessiana da log-posterior no MAP.
- Thompson sample: `w_a_sample ~ N(mu_a, Sigma_a)` via `numpy.random.multivariate_normal`.
- Decisão: `arm = argmax_a sigmoid(x^T w_a_sample)`.

Armazenamento em `bandit_state`:
- `arm` (PK), `feature_names_json`, `mu_json` (vetor), `sigma_json` (matriz flatten), `n_obs`, `updated_at`.

Se `n_obs < 1` (braço zerado): amostra do prior. Se `n_obs < 5`: amostra do prior com pequena perturbação pelos dados (regularização forte). Se ≥ 5: Laplace cheio.

## Hook de reward

```
classify_and_reward(conversation_id, inbound_msg_id):
  dispatch = query rewarm_dispatches abertos para conversation_id
  se nenhum aberto dentro de 48h: return
  history_since = messages da conversa desde dispatch.sent_at
  decision = Haiku (prompt PRODUCTIVE_TOOL, action ∈ {produtiva, nao_produtiva})
  productive = 1 se produtiva else 0
  update dispatch:
    responded_at = inbound_msg.created_at
    productive = productive
    reward = productive
    closed_at = now
```

Chamado como `asyncio.create_task` do webhook, não bloqueia resposta HTTP.

## Cuidados operacionais

1. **Idempotência do dispatch diário**: `cron_runs` com UNIQUE(slot_key, DATE). Se o loop tick dispara 2x, segundo é no-op.
2. **Corrida entre cron e webhook**: inbound pode chegar durante o dispatch matinal. O SELECT de candidatos filtra por última mensagem em D-1; se inbound chegar após a seleção, o candidato ainda é dispatched mas o próprio webhook cancela o `scheduled_send` por `client_replied`. Mantém-se correto.
3. **Haiku falhando no classificador**: se a classificação lança exceção, dispatch permanece aberto. O cron noturno fecha com `reward=0` e `productive=null` (sinaliza que falhou). Sem feedback fantasma.
4. **Não-estacionariedade**: v1 ignora. O refit usa janela infinita (tudo que tem). Se em 3-4 meses notarmos drift, adicionamos janela deslizante de 60-90 dias no refit.
5. **Volume explodindo**: se passar de 50/dia, o `run_batch` manual existente pode ficar lento por causa do rate limit 40-100s entre envios. Mas aqui o pipeline NÃO usa `run_batch` — cada lead é independente em `scheduled_sends` e o scheduler processa quando a hora chega. Não há limite de throughput artificial. Se Evolution API reclamar, ajustamos na frente.

6. **Timezone em send_at**: o scheduler compara `scheduled_sends.send_at` com `datetime('now')` do SQLite, que é **UTC**. O `compute_slot_datetime` retorna datetime tz-aware em America/Sao_Paulo (o slot 12:30 BRT em consciência operacional), e antes de persistir em `send_at` fazemos conversão explícita para UTC via `format_send_at_utc`. Sem essa conversão, um slot 12:30 BRT viraria string "2026-04-17 12:30:00" e dispararia às 12:30 UTC (09:30 BRT), três horas cedo. Preservada por `test_format_send_at_utc_converts_local_to_utc` e assertion inline em `test_daily_dispatch_creates_scheduled_send_and_dispatch`.

7. **Reinício durante a janela do slot**: `_maybe_run_slot` só dispara quando `now.hour == slot_hour` e `now.minute >= slot_minute`. Se o container reiniciar entre 10:30 e 10:59, o slot matinal daquele dia é pulado. Aceitável para v1 dado o volume. Mitigação simples se necessário no futuro: ampliar a janela de elegibilidade para 10:30-11:59 e deixar o lock da tabela `cron_runs` garantir idempotência.

## O que NÃO está neste change

- Bandit não-contextual como fallback. Omitido porque contextual com warmup não é frágil o suficiente para justificar a camada extra.
- Reward com múltiplos níveis (produtiva/neutra/tóxica). Omitido por simplicidade. Binário já captura o sinal principal.
- Exploração estratificada por origem do lead. Omitido até termos volume.
- UI para inspecionar estado do bandit (mu/sigma, alocação histórica). Omitido do change; pode vir depois via endpoint admin simples se necessário.
- Adaptação do cron pra dias úteis/fim de semana. V1 roda 7 dias/semana; Haiku já skipa conversas que claramente não devem ser tocadas.
