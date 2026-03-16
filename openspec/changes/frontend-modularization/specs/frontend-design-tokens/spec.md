## ADDED Requirements

### Requirement: CSS Custom Properties as Design Tokens
Valores de design (cores, espaçamento, border-radius, fontes) devem ser definidos como CSS custom properties em `css/tokens.css` e referenciados em todos os outros arquivos CSS.

#### Scenario: Token de cor primária
- **WHEN** qualquer componente usa a cor primária do app (#25D366)
- **THEN** o CSS referencia `var(--color-primary)` em vez do valor literal

#### Scenario: Tokens de espaçamento
- **WHEN** padding ou margin é aplicado a um componente
- **THEN** o CSS usa tokens de espaçamento (`var(--space-sm)`, `var(--space-md)`, etc.) para valores recorrentes

#### Scenario: Tokens de border-radius
- **WHEN** border-radius é aplicado
- **THEN** o CSS usa tokens (`var(--radius-sm)`, `var(--radius-md)`, `var(--radius-lg)`) em vez de valores literais

### Requirement: CSS Split by Feature
O CSS inline no index.html deve ser extraído para arquivos separados por feature, cada um importado via `<link>` no HTML.

#### Scenario: Nenhum CSS inline no index.html
- **WHEN** o refactor está completo
- **THEN** index.html não contém nenhum bloco `<style>` nem atributos `style=""` em elementos HTML

#### Scenario: Arquivos CSS por domínio
- **WHEN** o CSS é organizado
- **THEN** existem arquivos separados para: tokens, base/layout, sidebar, compose/drafts, context-panel, knowledge, review, campaigns, settings, mobile
