## Capability: rewarm-agent (update)

Delta sobre a capability existente.

### Mudança

A seleção de candidatos passa a aceitar uma **data de referência** arbitrária, em vez de sempre usar "ontem" fixo.

### Invariantes novas

- **I10. Seleção por data de referência.** `select_rewarm_candidates` aceita `reference_date` opcional em formato ISO `YYYY-MM-DD`. O filtro temporal passa a ser `DATE(MAX(messages.created_at)) = reference_date` para cada conversa, no lugar de `= DATE('now', '-1 day')`.
- **I11. Default ontem local.** Se `reference_date` não é fornecido, usa a data local de ontem (`now_local() - 1 day`).
- **I12. Sugestão por dia da semana.** Endpoint `GET /rewarm/suggested-date` retorna a data ideal pro default do seletor na UI. Segunda-feira (weekday=0) → sexta-feira passada (3 dias atrás). Qualquer outro dia → ontem. Sem tratamento de feriado.
- **I13. Sem validação de range.** Qualquer data ISO válida é aceita, incluindo futuro e passado distante. O risco de escolhas esquisitas é operacional (lista vazia ou com leads ativos), não técnico.

### Endpoints

- **`POST /rewarm/preview`** (modificado): corpo opcional `{"reference_date": "YYYY-MM-DD"}`. Sem corpo, mantém comportamento anterior (ontem). Retorno e forma dos items inalterados.
- **`GET /rewarm/suggested-date`** (novo): retorna `{"date": "YYYY-MM-DD", "label": "nome-do-dia-em-portugues"}`.

### UX (contrato)

- Botão na sidebar rotulado como **"Reesquentar leads"** (antes: "Reesquentar D-1").
- Clique no botão abre modal intermediário de escolha de data antes de gerar preview.
- Modal oferece: "Ontem", a data sugerida (se diferente de ontem), e input livre `type=date`.
- Confirmação no modal dispara `POST /rewarm/preview` com `reference_date` selecionada e abre o modal de revisão já existente.
- Modal de revisão exibe a data de referência usada no header para transparência.
