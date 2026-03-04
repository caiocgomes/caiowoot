## 1. CSS

- [x] 1.1 Adicionar estilo `.msg-time` para horário dentro do balão (font-size: 11px, cor secundária, float right)
- [x] 1.2 Adicionar estilo `.date-separator` para separador de data centralizado entre mensagens

## 2. JavaScript

- [x] 2.1 Criar função `formatTimeShort(dateStr)` que retorna sempre HH:MM em America/Sao_Paulo
- [x] 2.2 Criar função `formatDateSeparator(dateStr)` que retorna "Hoje" ou "DD de mês"
- [x] 2.3 Modificar `appendMessage(msg)` para renderizar timestamp HH:MM no balão
- [x] 2.4 Modificar `appendMessage(msg)` para inserir separador de data quando dia muda (comparar com mensagem anterior)

## 3. Verificação

- [x] 3.1 Testar com mensagens de hoje, ontem e dias anteriores
- [x] 3.2 Testar com mensagens sem `created_at` (graceful degradation)
- [x] 3.3 Verificar aparência no mobile
