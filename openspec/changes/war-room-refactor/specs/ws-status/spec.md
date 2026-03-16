## ADDED Requirements

### Requirement: WebSocket Connection Status Indicator

Indicador visual no sidebar header mostrando o estado da conexão WebSocket em tempo real, para que o operador saiba se está recebendo atualizações.

#### Scenario: WebSocket conectado

- **WHEN** WebSocket is OPEN
- **THEN** green dot appears in sidebar header

#### Scenario: WebSocket desconectado ou com erro

- **WHEN** WebSocket is CLOSED or ERROR
- **THEN** red dot appears in sidebar header

#### Scenario: WebSocket reconecta

- **WHEN** WebSocket reconnects
- **THEN** dot changes back to green
