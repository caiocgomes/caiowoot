## Cenários

### Seleção parametrizada (`tests/test_rewarm_query.py`)

- **[given] conversa com última mensagem há 1 dia [when] select_rewarm_candidates sem parâmetro [then]** aparece (default = ontem).
- **[given] conversa com última mensagem há 3 dias [when] select sem parâmetro [then]** não aparece.
- **[given] conversa com última mensagem em data específica X [when] select com reference_date=X [then]** aparece.
- **[given] conversa com última mensagem em data Y [when] select com reference_date=X (Y≠X) [then]** não aparece.

### suggested-date (`tests/test_rewarm_suggested_date.py`)

- **[given] hoje é segunda-feira [when] GET /rewarm/suggested-date [then]** retorna `{date: sexta_iso, label: "sexta-feira"}`.
- **[given] hoje é terça [when] suggested-date [then]** retorna `{date: ontem_iso, label: "segunda-feira"}` (label = dia da semana da data sugerida).
- **[given] hoje é sábado [when] suggested-date [then]** retorna ontem (sexta).
- **[given] hoje é domingo [when] suggested-date [then]** retorna ontem (sábado).
- Formato `YYYY-MM-DD` sempre.
- Label sempre em português.

### Endpoints (`tests/test_rewarm_routes.py`)

- **[given] candidatos seed pra ontem [when] POST /rewarm/preview sem body [then]** retorna esses candidatos.
- **[given] candidatos seed pra 5 dias atrás [when] POST /rewarm/preview body=`{reference_date: "<5 dias atrás>"}` [then]** retorna esses candidatos.
- **[given] body com reference_date malformada [when] POST /rewarm/preview [then]** 422.
