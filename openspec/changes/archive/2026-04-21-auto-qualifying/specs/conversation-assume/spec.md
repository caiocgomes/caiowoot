## ADDED Requirements

### Requirement: Assumir conversa manualmente
O operador pode assumir uma conversa em qualifying a qualquer momento, parando o robô.

#### Scenario: Operador clica "Assumir conversa"
- **WHEN** o operador clica no botão "Assumir conversa" numa conversa com `is_qualified = False`
- **THEN** `is_qualified` é setado para True, o banner de qualifying desaparece, a área de composição normal aparece, e a sidebar atualiza a cor

#### Scenario: Próxima mensagem após assumir
- **WHEN** o lead envia mensagem após o operador assumir
- **THEN** o fluxo normal acontece (gerar drafts para operador), o robô não interfere mais

#### Scenario: is_qualified é permanente
- **WHEN** is_qualified é setado para True (por handoff automático ou manual)
- **THEN** nunca volta para False, independente de qualquer ação
