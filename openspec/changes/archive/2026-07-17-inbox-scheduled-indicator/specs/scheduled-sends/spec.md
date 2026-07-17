## MODIFIED Requirements

### Requirement: Display scheduled sends in the UI
The system SHALL show pending scheduled sends in the conversation view and indicate conversations with pending sends in the conversation list via a yellow vertical line on the right edge of the conversation row.

#### Scenario: Conversation has a pending scheduled send
- **WHEN** the operator opens a conversation with a pending scheduled send
- **THEN** the UI SHALL display a pill/banner showing the scheduled time, a preview of the message content, and a cancel button

#### Scenario: Conversation list with scheduled sends
- **WHEN** a conversation has one or more pending scheduled sends (status `pending` and `send_at > now()`)
- **THEN** the conversation list row SHALL receive a CSS modifier class (`has-scheduled`) that renders a 3px yellow vertical line (`var(--color-warning)`) on the right edge of the row
- **AND** the row SHALL NOT display a clock emoji or any inline icon next to the contact name for this purpose

#### Scenario: Conversation list with multiple pending scheduled sends
- **WHEN** a single conversation has two or more pending scheduled sends
- **THEN** the conversation list row SHALL display exactly one yellow vertical line on the right edge (visual treatment is independent of count)

#### Scenario: Conversation list without scheduled sends
- **WHEN** a conversation has no pending scheduled sends (none exist, or all are cancelled/sent/failed)
- **THEN** the conversation list row SHALL NOT have the `has-scheduled` modifier class and the right border SHALL be absent

#### Scenario: Scheduled send is cancelled or sent
- **WHEN** the WebSocket receives a `scheduled_send_cancelled` or `scheduled_send_completed` event
- **THEN** the UI SHALL remove the scheduled send indicator from the conversation view and update the conversation list row (removing the `has-scheduled` class if no other pending sends remain for that conversation)

#### Scenario: New scheduled send is created
- **WHEN** the WebSocket receives a `scheduled_send_created` event for a conversation
- **THEN** the conversation list row for that conversation SHALL receive the `has-scheduled` modifier class
