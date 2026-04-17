## Schema

- [ ] Adicionar migrations em `app/database.py` (MIGRATIONS list):
  - `rewarm_dispatches_table`: id, conversation_id FK, features_json, arm, scheduled_send_id FK nullable, scheduled_for, sent_at nullable, responded_at nullable, productive nullable, reward nullable, closed_at nullable, converted_at nullable, status (pending/sent/skipped_client_replied/closed), created_at.
  - `bandit_state_table`: arm PK, feature_names_json, mu_json, sigma_json, n_obs, updated_at.
  - `cron_runs_table`: id, slot_key, ran_at. Unique index em (slot_key, DATE(ran_at)).
  - Index em `rewarm_dispatches(conversation_id, responded_at)` para hook de reward.

## Bandit

- [ ] Criar `app/services/rewarm_bandit.py`:
  - `FEATURE_NAMES = ["intercept", "has_history", "hora_resp_tipica", "estagio_link"]`.
  - `async def extract_features(db, conversation_id) -> dict`: calcula mediana de horários de inbound histórico, faz encoding.
  - `def features_to_vector(features) -> np.ndarray`: dict para vetor ordenado.
  - `async def sample_arm(db, features) -> str`: se `total_dispatches < 40`, retorna random.choice(['noon','evening']); senão, Thompson sample. Retorna "noon" ou "evening".
  - `async def refit_posterior(db) -> None`: para cada braço, faz Laplace em cima dos dispatches fechados, grava em `bandit_state`.
  - `async def classify_response_productive(db, conversation_id, sent_at) -> bool`: chama Haiku com PRODUCTIVE_TOOL. Retorna True se produtiva.
  - `async def compute_slot_datetime(arm, now_local) -> datetime`: retorna datetime com jitter.
  - `_laplace_fit(X, y, prior_sigma=3.0) -> (mu, Sigma)`: Newton-Raphson, hessiana analítica.

## Cron

- [ ] Criar `app/services/rewarm_cron.py`:
  - `CRON_SLOTS = {"morning": (10, 30), "nightly": (2, 0)}`.
  - `async def _slot_already_ran(db, slot_key) -> bool`: checa cron_runs.
  - `async def _mark_slot_ran(db, slot_key) -> None`.
  - `async def daily_dispatch() -> dict`: seleciona candidates, extract features, sample arm, decide conteúdo via `decide_rewarm_action`, cria scheduled_send + dispatch.
  - `async def nightly_closeout() -> dict`: fecha dispatches stale, refit posterior.
  - `async def rewarm_cron_loop()`: loop infinito com `asyncio.sleep(60)`, checa hora, dispara slots quando batem.

## Integrações

- [ ] Patch `app/services/scheduler.py` `_process_due_sends`: ao marcar `scheduled_send` como `sent`, se `created_by='rewarm_agent'`, faz UPDATE em `rewarm_dispatches` correspondente (pelo `scheduled_send_id`) setando `sent_at=now`.

- [ ] Patch `app/routes/webhook.py`: depois de gravar inbound, disparar `asyncio.create_task(rewarm_bandit.handle_reward_inbound(conversation_id, msg_id))` que procura dispatch aberto, classifica via Haiku, grava reward.

- [ ] Patch `app/main.py`: adicionar `rewarm_cron_task = asyncio.create_task(rewarm_cron_loop())` ao lifespan.

## Testes

- [ ] `tests/test_rewarm_bandit.py`:
  - `test_extract_features_no_history`: conversa sem inbound → has_history=0.
  - `test_extract_features_with_history`: conversa com 3 inbounds → hora_resp_tipica = mediana em decimal.
  - `test_sample_arm_warmup`: com <40 dispatches, alocação é aproximadamente 50/50 em 100 amostras.
  - `test_sample_arm_thompson`: com dispatches desbalanceando um braço como claramente melhor, Thompson aloca preferencialmente nesse braço.
  - `test_refit_posterior_idempotent`: refit 2x seguidos produz mesmo mu/sigma.
  - `test_classify_response_mocks_haiku`: mock do client Haiku retornando produtiva/não-produtiva.

- [ ] `tests/test_rewarm_cron.py`:
  - `test_slot_idempotent`: roda daily_dispatch 2x no mesmo dia, segundo é no-op.
  - `test_dispatch_respects_auto_send_flag`: flag off → no-op.
  - `test_dispatch_creates_scheduled_send_and_dispatch`: flag on + candidato válido → uma linha em cada tabela.

- [ ] `tests/test_rewarm_reward_hook.py`:
  - `test_inbound_triggers_classification`: mock Haiku, garante que responded_at/productive são gravados.
  - `test_inbound_ignored_no_open_dispatch`: sem dispatch, nada acontece.
  - `test_inbound_ignored_past_48h`: dispatch com sent_at > 48h → não classifica.

- [ ] `tests/test_scheduler_rewarm_sent_at.py`:
  - `test_scheduled_send_marks_dispatch_sent_at`: scheduler processa send de rewarm → dispatch.sent_at é preenchido.

## Qualidade

- [ ] Rodar pytest full suite.
- [ ] Rodar `uv run uvicorn` localmente, esperar cron matinal OU forçar via endpoint interno de teste.
- [ ] Monitorar primeiros 3 dias de produção e ajustar warmup/janelas se necessário.
