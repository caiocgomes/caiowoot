## ADDED Requirements

### Requirement: View Manager
Um módulo `js/router.js` deve gerenciar a navegação entre views, substituindo a lógica manual de show/hide espalhada por múltiplas funções.

#### Scenario: Navegar para uma view
- **WHEN** `navigate('campaigns')` é chamado
- **THEN** todos os elementos de sidebar-content e main-content são escondidos, e apenas os elementos correspondentes à view 'campaigns' são mostrados

#### Scenario: Adicionar uma nova view
- **WHEN** uma nova feature precisa de uma view
- **THEN** basta adicionar uma entrada no registro de views do router (um objeto), sem modificar nenhuma outra view existente

#### Scenario: Tab ativa sincronizada
- **WHEN** uma view é ativada via navigate()
- **THEN** a tab correspondente no sidebar recebe a classe `.active` e as demais perdem

#### Scenario: View com sub-views
- **WHEN** uma view tem sub-views (ex: campaigns tem list, form, detail)
- **THEN** navigate('campaign-form') mostra o sidebar de campaigns E o main de campaign-form, sem lógica especial no caller

### Requirement: Global Function Bridge
Funções chamadas via `onclick=""` no HTML devem ser expostas no escopo global durante a migração.

#### Scenario: onclick handler em ES module
- **WHEN** o HTML contém `onclick="openConversation(id)"`
- **THEN** main.js expõe `window.openConversation` apontando para a função do módulo correspondente
