## Context

O layout do chat usa flexbox vertical: `#main` (flex-col) contém `#chat-header`, `#messages` (flex:1, overflow-y:auto) e `#compose`. Em teoria, apenas `#messages` deveria scrollar. Na prática, em mobile (especialmente Safari iOS), o container flex não restringe corretamente a altura dos filhos quando falta `min-height: 0` no pai, fazendo o body inteiro scrollar e o header sumir.

## Goals / Non-Goals

**Goals:**
- Header do chat fica visível durante scroll de mensagens no mobile
- Sem regressão no layout desktop

**Non-Goals:**
- Redesenhar o layout do chat
- Mudar comportamento de navegação (toggle sidebar, etc.)

## Decisions

**Decisão: `min-height: 0` no `#main` + `position: sticky` como safety net**

O fix principal é adicionar `min-height: 0` ao `#main` no mobile. Isso resolve o problema clássico de flexbox onde o container flex não limita a altura dos filhos, permitindo que `#messages` respeite seu `overflow-y: auto`.

Como safety net, o `#chat-header` recebe `position: sticky; top: 0; z-index: 10` no mobile. Isso garante que mesmo em edge cases (teclado virtual, rotação de tela) o header permaneça visível.

Alternativa descartada: `position: fixed`. Criaria problemas de espaçamento e precisaria de padding-top compensatório no `#messages`.

## Risks / Trade-offs

- [Safari iOS viewport changes] -> O `100dvh` já está no body, o que mitiga a maioria dos problemas. O sticky é a segunda camada de proteção.
- [z-index conflict] -> z-index 10 é suficiente, sidebar overlay usa z-index 100.
