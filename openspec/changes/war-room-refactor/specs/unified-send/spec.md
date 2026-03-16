## ADDED Requirements

### Requirement: Unified Message Send Service

Consolidar a lógica de envio de mensagens (texto e arquivo) num único serviço `message_sender` que encapsula todo o fluxo: envio via Evolution API, inserção no banco, registro de edit_pair, disparo de annotation em background e broadcast via WebSocket.

#### Scenario: Envio de mensagem somente texto

- **WHEN** operator sends text-only message
- **THEN** `message_sender.send_and_record` handles everything (send, insert, edit_pair, annotation, broadcast)

#### Scenario: Envio de mensagem com arquivo

- **WHEN** operator sends message with file
- **THEN** same `send_and_record` handles it with file parameter

#### Scenario: Draft selecionado antes do envio

- **WHEN** draft was selected
- **THEN** edit_pair is recorded with original vs final

#### Scenario: Falha no envio

- **WHEN** send fails
- **THEN** error is returned without partial state
