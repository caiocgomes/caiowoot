## Why

A aba Aprendizado está incompleta: após validar, rejeitar ou promover uma anotação, ela desaparece sem deixar rastro. O operador não tem como ver regras ativas, histórico de decisões, ou entender o estado atual do aprendizado. Além disso, o stat "confirmadas" na lista de pendentes é confuso (se refere a drafts aceitos sem edição, não a anotações já validadas).

## What Changes

- Adicionar seção de regras ativas na aba Aprendizado (listar, toggle on/off, editar texto)
- Adicionar stats de histórico no endpoint GET /review (total já validado, rejeitado, promovido)
- Corrigir labels dos stats para serem mais claros
- Permitir ver o histórico de anotações já revisadas (com filtro)

## Capabilities

### New Capabilities
Nenhuma.

### Modified Capabilities
- `learning-review`: Adicionar stats de histórico e endpoint de histórico
- `inbox-ui`: Adicionar seção de regras e histórico na aba Aprendizado

## Impact

- **Backend**: Modificar GET /review para incluir stats de histórico, adicionar GET /review/history
- **Frontend**: Modificar aba Aprendizado em index.html e app.js
- **Sem novas dependências**
