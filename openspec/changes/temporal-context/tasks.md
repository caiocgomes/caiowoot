## 1. Histórico com timestamps

- [x] 1.1 Modificar `_build_conversation_history` para incluir `created_at` na query e retornar timestamps junto com as mensagens
- [x] 1.2 Formatar as últimas 10 mensagens com `[HH:MM]` (hoje) ou `[DD/MM HH:MM]` (dias anteriores), mensagens mais antigas sem timestamp

## 2. Contexto temporal no prompt

- [x] 2.1 Criar função que calcula o tempo decorrido desde a última mensagem inbound e formata a seção de contexto temporal
- [x] 2.2 Adicionar seção "Contexto temporal" em `_build_prompt_parts` após o histórico de conversa e antes da instrução de geração

## 3. System prompt

- [x] 3.1 Adicionar orientação no `SYSTEM_PROMPT` para a LLM considerar o contexto temporal: reconhecer atrasos significativos (> 1h) sem ser excessivamente apologética, ajustar cumprimento ao horário do dia

## 4. Testes

- [x] 4.1 Teste de formatação de timestamps: mensagens de hoje com `[HH:MM]`, mensagens de dias anteriores com `[DD/MM HH:MM]`, mensagens além das últimas 10 sem timestamp
- [x] 4.2 Teste de contexto temporal: cálculo correto de tempo decorrido, formatação para atrasos > 1h e < 1h
- [x] 4.3 Teste de integração: prompt gerado contém seção de contexto temporal e timestamps nas mensagens recentes
