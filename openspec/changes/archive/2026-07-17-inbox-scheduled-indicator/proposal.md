## Why

A inbox hoje já mostra um relógio 🕑 ao lado do nome de conversas com envio agendado pendente, mas o emoji é pequeno, mistura com o nome e passa batido no scan vertical de uma lista densa. Quero um marcador glanceable que diga "essa conversa tem coisa agendada acontecendo" sem precisar ler cada linha. Uma faixa vertical amarela na borda direita da row resolve isso porque ocupa altura inteira da row, fica numa coluna visual estável e dá leitura periférica.

Bônus: o token `var(--color-warning)` (amarelo) já é usado como `border-left` em `.conv-item.qualifying`. Botar o indicador de scheduled na **direita** com a mesma cor cria simetria semântica: esquerda = bot está qualificando, direita = tem mensagem agendada saindo. Mesma família visual, eixos distintos.

## What Changes

- Substituir o emoji `🕑` (classe `.conv-clock`) por um `border-right: 3px solid var(--color-warning)` em `.conv-item` quando a conversa tem `has_scheduled = true`.
- Aplicar via classe modificadora (ex: `.conv-item.has-scheduled`) para manter o estado consultável por outros estilos no futuro.
- Limpar o span `.conv-clock` do markup e a regra CSS associada.
- Critério de "ativa" mantido: apenas pending com `send_at > now()` (já é o que o backend retorna em `has_scheduled` — sem mudança de query).
- Múltiplas agendadas na mesma conversa: linha única (mesmo visual independente da quantidade).
- Sem mudança de API, schema ou backend.

## Capabilities

### New Capabilities
Nenhuma.

### Modified Capabilities
- `scheduled-sends`: o requirement "Display scheduled sends in the UI" tem um scenario que descreve "clock icon indicator next to that conversation" — passa a especificar "yellow vertical line on the right edge of the conversation row". O `inbox-ui` não precisa de delta porque o ownership do visual de scheduled-sends já está em `scheduled-sends` (única fonte da verdade pra esse indicador específico).

## Impact

Frontend:
- `app/static/js/ui/conversations.js:55` — remover construção do span `.conv-clock`, adicionar classe `has-scheduled` no `.conv-item` quando `conv.has_scheduled`.
- `app/static/app.js:220` — rendering duplicado da mesma row, precisa do mesmo tratamento (ou consolidar, mas isso é fora do escopo dessa change).
- `app/static/css/sidebar.css` — remover regra `.conv-clock`, adicionar `.conv-item.has-scheduled { border-right: 3px solid var(--color-warning); }`.

Backend:
- Nenhuma mudança. O campo `has_scheduled` (`app/routes/conversations.py:50`) já existe e já filtra por `send_at > now()` e `status = 'pending'`.

Reatividade:
- WebSocket events `scheduled_send_created`, `scheduled_send_cancelled`, `scheduled_send_completed` já recarregam a lista hoje (responsável pelo emoji aparecer/sumir). O mesmo caminho serve para a linha amarela — confirmar no momento da implementação que o reload bate na nova classe.

Riscos:
- Conflito visual com `.conv-item.active` (que tem `border-left` 3px solid). Como o novo indicador é na direita, não colide. Verificar no Playwright que ambos coexistem.
- Daltonismo: amarelo+luminância média pode ser difícil de distinguir do background em alguns modos. Mitigação: a linha tem 3px (mesma espessura do indicador esquerdo de qualifying), e o token `--color-warning` já passou pelo design system. Não vamos resolver acessibilidade de cor nessa change — fica como dívida se aparecer.
