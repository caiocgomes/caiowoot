## 1. CSS

- [x] 1.1 Em `app/static/css/sidebar.css`: remover regra `.conv-clock { ... }` (linha 50).
- [x] 1.2 Em `app/static/css/sidebar.css`: adicionar regra `.conv-item.has-scheduled { border-right: 3px solid var(--color-warning); }` próxima às outras regras de modificadores de `.conv-item` (perto de `.qualifying`).

## 2. Renderização da row

- [x] 2.1 Em `app/static/js/ui/conversations.js`: remover a construção do span `.conv-clock` (linha 55) e o uso dele no template HTML da row (linha 59).
- [x] 2.2 Em `app/static/js/ui/conversations.js`: adicionar a classe `has-scheduled` ao `.conv-item` raiz quando `conv.has_scheduled === true`. Manter classes existentes (`is-new`, `needs-reply`, `qualifying`, `active`) coexistindo.
- [x] 2.3 ~~Aplicar o mesmo tratamento em `app/static/app.js:220` (rendering duplicado).~~ **SKIPPED**: `app.js` é dead code, não é carregado por `index.html` (que só importa `js/main.js`). Editar dead code adiciona ruído. Marcar como dívida separada se for relevante limpar.

## 3. Reatividade WebSocket

- [x] 3.1 Verificado: `app/static/js/main.js:162` (`scheduled_send_created`) chama `loadConversations()` que re-fetcha a lista. O backend retorna `has_scheduled` atualizado, então a classe `.has-scheduled` aparece automaticamente sem código novo.
- [x] 3.2 Verificado: `main.js:169` (`scheduled_send_cancelled`) e `main.js:176` (`scheduled_send_completed`) também chamam `loadConversations()`. A classe some quando o backend deixa de reportar pendente.

## 4. Verificação visual

- [ ] 4.1 Rodar `uv run uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload`, abrir o frontend em um navegador. **PENDENTE — manual.**
- [ ] 4.2 Criar uma conversa com mensagem agendada (via UI ou inserção direta). Confirmar que a row tem linha amarela na direita e NÃO tem emoji 🕑. **PENDENTE — manual.** (Cobertura automatizada via `test_scheduled_indicator.py`.)
- [ ] 4.3 Cancelar a mensagem agendada. Confirmar que a linha some. **PENDENTE — manual.** (Implicitamente coberto pelo cleanup nos testes e2e.)
- [ ] 4.4 Confirmar que `.conv-item.active` (left border) e `.has-scheduled` (right border) coexistem visualmente sem conflito quando a conversa selecionada tem agendamento. **PENDENTE — manual.**
- [ ] 4.5 Confirmar que `.qualifying` (left border amarelo) e `.has-scheduled` (right border amarelo) coexistem na mesma row se uma conversa estiver simultaneamente em qualifying e com agendamento. **PENDENTE — manual.**

## 5. Testes e2e

- [x] 5.1 Criado `tests/e2e/test_scheduled_indicator.py` com 4 testes: classe presente quando pending, border-right 3px solid yellow, ausência do `.conv-clock` e do emoji 🕑, classe ausente sem pending. Todos passam.
- [x] 5.2 Grep confirma: nenhum teste e2e existente referencia `.conv-clock` ou 🕑 na lista de conversas. Único uso remanescente do emoji é em `schedule.js:42` (pill grande dentro da conversa aberta, `.scheduled-pill-icon`), fora do escopo.

## 6. Limpeza e validação

- [x] 6.1 `grep -rn "conv-clock\|1F551\|🕑" app/` retorna apenas: `app.js` (dead code, não carregado) e `schedule.js:42`/`app.js:1448` (pill grande, fora do escopo). Zero ocorrências no caminho live da lista de conversas.
- [x] 6.2 `uv run pytest tests/test_scheduled_sends.py -v` — 11/11 backend tests pass. `uv run pytest tests/e2e/test_scheduled_indicator.py tests/e2e/test_inbox_ui.py -v` — 8/8 e2e tests pass.
- [x] 6.3 `openspec validate inbox-scheduled-indicator` — "Change is valid".
