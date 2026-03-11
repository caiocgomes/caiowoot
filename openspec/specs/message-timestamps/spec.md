## ADDED Requirements

### Requirement: Mensagens exibem horario de envio

Cada mensagem no chat SHALL exibir o horario (HH:MM) no canto inferior direito do balao. O horario MUST estar em timezone `America/Sao_Paulo`. Se `created_at` for null, o timestamp SHALL ser omitido.

#### Scenario: Mensagem com timestamp valido
- **WHEN** uma mensagem com `created_at = "2026-03-04 14:30:00"` e renderizada
- **THEN** o balao exibe "14:30" no canto inferior direito, em fonte menor e cor secundaria

#### Scenario: Mensagem sem timestamp
- **WHEN** uma mensagem com `created_at` null e renderizada
- **THEN** o balao e exibido sem horario (comportamento atual)

#### Scenario: Mensagem de ontem
- **WHEN** uma mensagem de um dia anterior e renderizada
- **THEN** o horario exibido no balao ainda e HH:MM (nao DD/MM)

### Requirement: Separador de data entre dias diferentes

Quando houver mudanca de dia entre mensagens consecutivas, o sistema SHALL inserir um separador visual centralizado com a data formatada. A primeira mensagem da conversa tambem SHALL ter separador.

#### Scenario: Mensagens do mesmo dia
- **WHEN** duas mensagens consecutivas tem `created_at` no mesmo dia
- **THEN** nenhum separador e inserido entre elas

#### Scenario: Mensagens de dias diferentes
- **WHEN** uma mensagem de 03/03 e seguida por uma de 04/03
- **THEN** um separador com "04 de marco" e exibido antes da segunda mensagem

#### Scenario: Primeira mensagem da conversa
- **WHEN** a primeira mensagem da conversa e renderizada
- **THEN** um separador com a data da mensagem e exibido antes dela

#### Scenario: Mensagem de hoje
- **WHEN** o separador e para o dia atual
- **THEN** o texto exibido e "Hoje" em vez da data
