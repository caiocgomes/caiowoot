## Why

O "Reesquentar D-1" atual seleciona conversas cuja última mensagem foi exatamente ontem. Isso quebra em dois cenários reais:

- Sexta à noite o lead manda mensagem. Caio não trabalha sábado/domingo. Segunda ele clica reesquentar e não acha mais nada, porque "ontem" é domingo e ninguém mandou mensagem no domingo; os leads de sexta já têm "última mensagem há 3 dias".
- Feriado no meio da semana: mesmo problema, desalinhando o filtro temporal com o último dia útil.

Hoje a única saída é editar `'-1 day'` no SQL e reiniciar. Inviável.

## What Changes

- `select_rewarm_candidates` aceita parâmetro `reference_date` (string ISO `YYYY-MM-DD`). Default continua sendo ontem local.
- `POST /rewarm/preview` aceita body opcional `{"reference_date": "..."}`. Sem body, mantém comportamento original (ontem).
- Novo `GET /rewarm/suggested-date`: retorna `{date, label}` com default inteligente por dia da semana (segunda → sexta; senão → ontem). Sem tratamento de feriado, decisão explícita pra manter simples.
- Botão na sidebar renomeado de "Reesquentar D-1" para **"Reesquentar leads"**.
- Novo modal pequeno (`rewarm-date-modal`) aparece antes do preview. Oferece:
  - Opção "Ontem" (sempre presente)
  - Opção "[Dia sugerido]" quando o sugerido é diferente de ontem (tipo segunda-feira oferecendo sexta)
  - Input de data livre pra qualquer outra escolha
- Sem limite de data. Passado longínquo é permitido (operador assume responsabilidade). Data futura/hoje também, já que o risco é operacional, não técnico.
- Modal de revisão existente ganha badge no topo mostrando qual data foi usada como referência.

## Capabilities

### Modified Capabilities
- `rewarm-agent`: seleção de candidatos agora aceita data de referência parametrizável. Semântica "mesma do filtro original" é preservada (leads cuja última mensagem foi exatamente nessa data).

## Impact

- **Modifica** `app/services/rewarm_engine.py`: assinatura de `select_rewarm_candidates` ganha `reference_date`.
- **Modifica** `app/routes/rewarm.py`: body aceita `reference_date`; novo endpoint `GET /rewarm/suggested-date`.
- **Modifica** `app/static/index.html`: renomeia botão, adiciona modal de escolha de data.
- **Modifica** `app/static/js/ui/rewarm.js`: fluxo de clique abre modal de data antes do preview; passa `reference_date` no POST.
- **Sem migration**. Sem dependência nova.
- Testes: 4-5 novos casos cobrindo parametrização, default, suggested-date em cada dia da semana, preview com body vazio.
