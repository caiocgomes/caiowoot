## ADDED Requirements

### Requirement: Campo de edição com mais linhas visíveis
O textarea de edição de mensagens (`#draft-input`) SHALL ter altura mínima de 200px e altura máxima de 500px, permitindo ao operador visualizar mais linhas de texto sem precisar rolar.

#### Scenario: Altura inicial do campo
- **WHEN** o operador abre uma conversa e visualiza o campo de edição
- **THEN** o campo SHALL ter altura mínima de 200px (~8-10 linhas de texto visíveis)

#### Scenario: Expansão automática com conteúdo
- **WHEN** o operador digita ou cola texto que ultrapassa a altura visível
- **THEN** o campo SHALL expandir automaticamente até no máximo 500px

#### Scenario: Redimensionamento manual preservado
- **WHEN** o operador arrasta a borda do campo para redimensionar
- **THEN** o campo SHALL permitir redimensionamento vertical (propriedade `resize: vertical` mantida)
