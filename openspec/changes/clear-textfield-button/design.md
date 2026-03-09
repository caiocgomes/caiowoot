## Context

Mudança puramente frontend. Botão de limpar texto no textarea de composição.

## Goals / Non-Goals

**Goals:**
- Um toque para limpar o textarea e resetar estado de draft

**Non-Goals:**
- Confirmação antes de limpar (ação é reversível via undo do browser ou selecionando draft de novo)

## Decisions

### Botão X inline no textarea
Botão pequeno (ícone X ou "Limpar") posicionado dentro ou ao lado do textarea, visível apenas quando há texto. Ao clicar: limpa texto, reseta `currentDraftId`, `currentDraftGroupId`, `selectedDraftIndex`, e esconde justification.

Sem mudanças no backend.

## Risks / Trade-offs

Nenhum risco relevante. Mudança isolada no frontend.
