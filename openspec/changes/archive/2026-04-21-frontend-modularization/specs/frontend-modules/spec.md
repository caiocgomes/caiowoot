## ADDED Requirements

### Requirement: ES Module Structure
O frontend deve ser organizado em ES modules nativos (`<script type="module">`), sem build step. Cada módulo tem responsabilidade única e exporta funções explícitas.

#### Scenario: Entry point carrega módulos
- **WHEN** index.html é carregado no browser
- **THEN** `js/main.js` é executado como ES module, importa todos os módulos de UI, e chama suas funções de inicialização

#### Scenario: Módulos de UI são independentes
- **WHEN** um módulo de UI (ex: campaigns.js) é editado
- **THEN** nenhum outro módulo de UI precisa ser alterado (a menos que a interface pública do módulo mude)

### Requirement: Centralized State
Estado da aplicação deve residir em um único módulo `js/state.js`, importado por quem precisar.

#### Scenario: Variáveis globais eliminadas
- **WHEN** o refactor está completo
- **THEN** não existem variáveis `let`/`var`/`const` no escopo global de nenhum arquivo JS (exceto o objeto `state` exportado por state.js)

### Requirement: Centralized API
Chamadas HTTP devem ser centralizadas em `js/api.js` com tratamento uniforme de auth (401 redirect).

#### Scenario: Chamada de API com sessão expirada
- **WHEN** qualquer chamada fetch retorna 401
- **THEN** o browser redireciona para `/login.html` independente de qual módulo originou a chamada

#### Scenario: Nenhum fetch direto em módulos de UI
- **WHEN** o refactor está completo
- **THEN** nenhum módulo em `js/ui/` contém chamadas `fetch()` diretas; todos usam funções exportadas por `js/api.js`

### Requirement: WebSocket Module
Conexão WebSocket e dispatch de eventos devem estar em `js/ws.js`.

#### Scenario: Módulos registram handlers de eventos WS
- **WHEN** um módulo precisa reagir a um evento WebSocket (ex: `new_message`, `campaign_progress`)
- **THEN** ele registra um handler via a API pública de ws.js, sem acessar o objeto WebSocket diretamente

### Requirement: Utility Module
Funções utilitárias (escapeHtml, formatTime, normalizeTimestamp, etc.) devem estar em `js/utils.js`.

#### Scenario: Funções utilitárias compartilhadas
- **WHEN** dois ou mais módulos precisam de formatação de data ou escape de HTML
- **THEN** ambos importam de `js/utils.js` (sem duplicação)
