## ADDED Requirements

### Requirement: Toast/Snackbar Component

Componente de notificação visual (toast/snackbar) para substituir todos os usos de `alert()` e `confirm()` nativos do browser por uma interface consistente e não-bloqueante.

#### Scenario: Exibição de toast

- **WHEN** `showToast` is called
- **THEN** a pill notification appears at top of screen

#### Scenario: Auto-dismiss do toast

- **WHEN** toast timeout expires
- **THEN** it fades out automatically

#### Scenario: Modal de confirmação

- **WHEN** `showConfirm` is called
- **THEN** a modal with 2 buttons appears (replacing native `confirm()`)

#### Scenario: Migração de alert() existentes

- **WHEN** any code calls `alert()`
- **THEN** it should use `showToast` instead (all 12+ occurrences migrated)
