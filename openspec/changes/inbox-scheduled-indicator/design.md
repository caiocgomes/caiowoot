## Context

A lista de conversas (sidebar esquerda) renderiza cada conversa via `renderConversation()` em `app/static/js/ui/conversations.js:55` (e um clone em `app/static/app.js:220` — código duplicado que veio do refactor de modularização e ainda não foi removido).

Hoje o indicador de "tem envio agendado" é um emoji 🕑 inline (span `.conv-clock`) ao lado do nome. O backend já fornece o flag `has_scheduled` via `app/routes/conversations.py:50` com a query correta (`status = 'pending' AND send_at > now()`).

Stakeholders: operadores que precisam fazer scan visual rápido da inbox. Constraint: não introduzir dependência nova, não mexer em backend, manter compatibilidade com WebSocket events que recarregam a lista.

## Goals / Non-Goals

**Goals:**
- Substituir o emoji 🕑 por uma linha vertical amarela na borda direita da row, renderizada via classe modificadora `.has-scheduled` em `.conv-item`.
- Manter o mesmo critério "ativa" (pending + send_at > now()) — sem mudança de query.
- Garantir que os eventos WebSocket existentes (`scheduled_send_created`, `scheduled_send_cancelled`, `scheduled_send_completed`) continuem disparando o reload da lista que liga/desliga o indicador.

**Non-Goals:**
- Resolver o code duplication entre `conversations.js` e `app.js:220`. Vou aplicar o mesmo tratamento nos dois pra não quebrar nada, mas a deduplicação fica como dívida.
- Adicionar tooltip, contagem, ou qualquer informação além da presença binária do indicador.
- Mudar o pill grande `.scheduled-pill` dentro da conversa aberta (esse já é informativo, fora do escopo).
- Acessibilidade de cor (daltonismo) — fica como dívida se aparecer feedback.

## Decisions

**D1: Classe modificadora no `.conv-item` em vez de elemento inline.**
Adicionar `.has-scheduled` na row e estilizar via `border-right: 3px solid var(--color-warning)`. Alternativa considerada: manter um span dedicado (`.conv-scheduled-line`) absolutamente posicionado. Rejeitada porque a classe modificadora é menos código, mais idiomática (segue o padrão de `.is-new`, `.needs-reply`, `.qualifying`) e o `border-right` ocupa altura inteira da row sem precisar de cálculo.

**D2: Ownership do visual fica em `scheduled-sends`, não em `inbox-ui`.**
A spec `scheduled-sends/spec.md` já tinha o scenario que descreve o visual ("clock icon indicator"). Modificar lá, sem duplicar em `inbox-ui`. Alternativa: spec compartilhado entre os dois. Rejeitada porque cria ambiguidade de fonte da verdade.

**D3: Não tocar no backend.**
O campo `has_scheduled` já cobre exatamente o critério "pending + futuro". Mudar a query agora seria mistura de escopo. Se no futuro o critério "ativa" mudar (ex: incluir failed), aí sim mexe no backend.

**D4: Manter o token `var(--color-warning)` (amarelo Veridian) reutilizando o mesmo usado em `.conv-item.qualifying`.**
Cria simetria semântica esquerda/direita (qualifying vs scheduled). Alternativa: criar token novo `--color-scheduled`. Rejeitada porque introduzir token novo pra um único uso é prematuro — se aparecer um terceiro uso de amarelo com semântica diferente, aí refatora.

## Risks / Trade-offs

- **Risco**: Confusão semântica entre o amarelo de `.qualifying` (esquerda) e o de `.scheduled` (direita). → Mitigação: posições distintas (left vs right border) e o `.qualifying` já tem o emoji 🤖 antes do nome, então a desambiguação é clara.
- **Risco**: Daltonismo (cerca de 8% dos homens têm algum déficit de percepção de cor) pode tornar a linha amarela pouco distinta do background. → Mitigação consciente: 3px de espessura ajuda; aceitamos o trade-off agora. Se houver feedback, evolui pra ícone + cor.
- **Risco**: O `app.js:220` (renderização duplicada) ficar dessincronizado com `conversations.js`. → Mitigação: tasks.md vai listar explicitamente os dois pontos pra editar; teste e2e visual cobre ambos os caminhos se algum ainda for executado em runtime.
- **Trade-off**: Não exibir contagem perde informação útil ("essa conversa tem 3 agendadas, aquela 1"). Aceito agora — operador clica e vê os pills dentro da conversa pra detalhar. Reavaliar se aparecer demanda.
