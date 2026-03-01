## Why

O draft engine monta o histórico de conversa sem nenhuma informação temporal. A LLM não sabe que horas são, quando cada mensagem foi enviada, nem há quanto tempo o cliente está esperando resposta. Isso gera drafts que ignoram atrasos (não pedem desculpa por demora), erram cumprimentos (boa tarde às 22h) e não percebem gaps temporais que mudam o contexto da conversa.

## What Changes

- Adicionar timestamps nas últimas mensagens do histórico de conversa enviado à LLM
- Incluir o horário atual e o tempo desde a última mensagem do cliente como contexto explícito no prompt
- Atualizar o system prompt para orientar a LLM a considerar contexto temporal nas respostas

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `draft-engine`: O prompt passa a incluir timestamps nas últimas mensagens e uma seção de contexto temporal (horário atual, tempo de espera do cliente)

## Impact

- `app/services/draft_engine.py`: modificação em `_build_conversation_history` para incluir timestamps e em `_build_prompt_parts` para adicionar seção temporal
- Aumento marginal no tamanho do prompt (timestamps + 1-2 linhas de contexto)
- Nenhuma mudança de banco, API ou dependências
