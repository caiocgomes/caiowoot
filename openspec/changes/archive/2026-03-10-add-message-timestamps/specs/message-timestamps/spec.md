## ADDED Requirements

### Requirement: Mensagens exibem horário de envio

Cada mensagem no chat SHALL exibir o horário (HH:MM) no canto inferior direito do balão. O horário MUST estar em timezone `America/Sao_Paulo`. Se `created_at` for null, o timestamp SHALL ser omitido.

#### Scenario: Mensagem com timestamp válido
- **WHEN** uma mensagem com `created_at = "2026-03-04 14:30:00"` é renderizada
- **THEN** o balão exibe "14:30" no canto inferior direito, em fonte menor e cor secundária

#### Scenario: Mensagem sem timestamp
- **WHEN** uma mensagem com `created_at` null é renderizada
- **THEN** o balão é exibido sem horário (comportamento atual)

#### Scenario: Mensagem de ontem
- **WHEN** uma mensagem de um dia anterior é renderizada
- **THEN** o horário exibido no balão ainda é HH:MM (não DD/MM)

### Requirement: Separador de data entre dias diferentes

Quando houver mudança de dia entre mensagens consecutivas, o sistema SHALL inserir um separador visual centralizado com a data formatada. A primeira mensagem da conversa também SHALL ter separador.

#### Scenario: Mensagens do mesmo dia
- **WHEN** duas mensagens consecutivas têm `created_at` no mesmo dia
- **THEN** nenhum separador é inserido entre elas

#### Scenario: Mensagens de dias diferentes
- **WHEN** uma mensagem de 03/03 é seguida por uma de 04/03
- **THEN** um separador com "04 de março" é exibido antes da segunda mensagem

#### Scenario: Primeira mensagem da conversa
- **WHEN** a primeira mensagem da conversa é renderizada
- **THEN** um separador com a data da mensagem é exibido antes dela

#### Scenario: Mensagem de hoje
- **WHEN** o separador é para o dia atual
- **THEN** o texto exibido é "Hoje" em vez da data
