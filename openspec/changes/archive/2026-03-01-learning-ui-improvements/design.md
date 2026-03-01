## Context

A aba Aprendizado já existe com lista de anotações pendentes e ações (OK/Errado/Promover). Faltam: visibilidade de regras, histórico e stats claros. Backend de regras (GET /rules, toggle, edit) já existe.

## Goals / Non-Goals

**Goals:**
- Mostrar regras ativas com toggle e edição inline
- Stats de histórico (validadas, rejeitadas, promovidas)
- Labels claros nos stats de pendentes
- Visibilidade do que já foi revisado

**Non-Goals:**
- Paginação (volume baixo)
- Filtros avançados no histórico
- Reabrir/reverter decisões de revisão

## Decisions

### Layout da aba Aprendizado

Dividir a sidebar em duas seções: "Pendentes" (lista atual) e "Regras" (lista de regras ativas). O main area mostra detalhe da anotação selecionada ou detalhe/edição da regra selecionada.

Stats de histórico ficam no topo da sidebar, sempre visíveis.

### Stats de pendentes: renomear labels

Atual: "pendentes / editadas / confirmadas" (confuso).
Novo: "pendentes / editadas / aceitas" (mais claro que "aceitas" = draft usado sem edição).

### Histórico como stats, não como lista

Com 10-20 conversas/dia, o histórico seria uma lista curta e pouco útil de navegar. Melhor mostrar apenas contadores (N validadas, M rejeitadas, K promovidas) do que uma lista completa. Se no futuro precisar, adiciona.

## Risks / Trade-offs

Nenhum relevante. Mudança puramente de UI sobre APIs que já existem.
