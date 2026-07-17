## Backend

- [ ] `app/services/rewarm_engine.py`:
  - Modificar `select_rewarm_candidates(db, reference_date: str | None = None)`. Quando `None`, default = ontem local ISO.
  - Query usa `= ?` ao invés de `= DATE('now', '-1 day')`. Recebe a data como binding.
- [ ] `app/routes/rewarm.py`:
  - `POST /rewarm/preview`: aceita body JSON opcional com `reference_date`. Sem body, usa default. Passa pra `select_rewarm_candidates`.
  - `GET /rewarm/suggested-date`: retorna `{date: "YYYY-MM-DD", label: "sexta-feira"}`. Lógica: se `weekday() == 0` (segunda), retorna sexta passada; senão, retorna ontem. Label é nome do dia da semana em português.

## Frontend

- [ ] `app/static/index.html`:
  - Renomear botão `#rewarm-d1-btn` texto para "Reesquentar leads".
  - Adicionar modal `#rewarm-date-modal` com 3 opções radio (ontem, sugerido-se-diferente, input type=date) e botões "Cancelar" e "Gerar sugestões".
- [ ] `app/static/js/ui/rewarm.js`:
  - Nova função `startRewarmLeads()` substituindo `startRewarmD1()` (mantém alias por compat).
  - Ao clicar, faz `GET /rewarm/suggested-date`, popula o modal de data, mostra.
  - Quando operador confirma, lê data escolhida, chama `POST /rewarm/preview {reference_date}`, fecha date-modal, abre modal de revisão existente.
  - Modal de revisão mostra badge/texto no header tipo "referência: 17/04/2026 (sexta)".
- [ ] `app/static/js/main.js`: export da nova função + binding no window.
- [ ] `app/static/css/rewarm.css`: estilos leves pro rewarm-date-modal (reutilizar classes do rewarm-modal).

## Testes

- [ ] `tests/test_rewarm_query.py` (existente): ajustar pra seed de data explícita + adicionar teste com `reference_date` customizada (ex: há 3 dias).
- [ ] Novo `tests/test_rewarm_suggested_date.py`: segunda → sexta; terça, quarta, quinta, sexta, sábado, domingo → ontem. Formato ISO + label em português.
- [ ] `tests/test_rewarm_routes.py`: preview com body vazio continua funcionando; preview com `reference_date` usa a data informada.

## Qualidade

- [ ] Suite verde.
- [ ] Rodar `uv run uvicorn` local e testar: clicar "Reesquentar leads", escolher ontem e data custom, validar preview.
