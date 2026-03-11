## ADDED Requirements

### Requirement: Schedule a text message for future delivery
The system SHALL allow the operator to schedule a text message to be sent at a specified future time. The scheduled send SHALL persist in the database and survive server restarts.

#### Scenario: Operator schedules a message with relative time
- **WHEN** the operator composes a message and selects a relative time option (30min, 1h, 2h)
- **THEN** the system SHALL store the message content, computed `send_at` timestamp, conversation ID, operator name, and optional draft metadata in `scheduled_sends` with status `pending`
- **THEN** the system SHALL broadcast a `scheduled_send_created` WebSocket event to all connected clients

#### Scenario: Operator schedules a message with preset time
- **WHEN** the operator selects "Amanha 9h" or "Amanha 14h"
- **THEN** the system SHALL compute `send_at` as the next occurrence of that time in the server's local timezone and store the scheduled send

#### Scenario: Operator schedules a message with custom datetime
- **WHEN** the operator selects a custom date and time
- **THEN** the system SHALL store the scheduled send with the specified `send_at` timestamp

#### Scenario: Scheduled send originates from a draft
- **WHEN** the operator schedules a message that was selected/edited from an AI draft
- **THEN** the system SHALL store `draft_id`, `draft_group_id`, and `selected_draft_index` in the scheduled send record for later edit_pair creation

### Requirement: Automatically send scheduled messages when due
The system SHALL run a background polling loop every 30 seconds that finds and sends all due scheduled messages.

#### Scenario: Scheduled message becomes due
- **WHEN** the polling loop finds a scheduled send with `send_at <= now()` and `status = 'pending'`
- **THEN** the system SHALL atomically transition the status to `sending`
- **THEN** the system SHALL send the message via Evolution API, insert it into the `messages` table as outbound, and update status to `sent` with `sent_at` timestamp
- **THEN** the system SHALL broadcast a `message_sent` WebSocket event

#### Scenario: Scheduled message from draft is sent
- **WHEN** a due scheduled send has draft metadata (draft_id, draft_group_id, selected_draft_index)
- **THEN** the system SHALL create an edit_pair record and trigger strategic annotation generation, identical to the immediate send flow

#### Scenario: Multiple scheduled sends are due simultaneously
- **WHEN** the polling loop finds multiple due messages
- **THEN** the system SHALL process each one independently (failure of one SHALL NOT prevent others from sending)

#### Scenario: Server restarts with pending scheduled sends
- **WHEN** the server starts and there are scheduled sends with `send_at` in the past and `status = 'pending'`
- **THEN** the polling loop SHALL pick them up on its first iteration and send them

#### Scenario: Evolution API fails during scheduled send
- **WHEN** the Evolution API returns an error while sending a scheduled message
- **THEN** the system SHALL set the status back to `pending` so the next polling cycle retries

### Requirement: Auto-cancel scheduled sends when client replies
The system SHALL cancel all pending scheduled sends for a conversation when an inbound message arrives from the client.

#### Scenario: Client sends message while scheduled send is pending
- **WHEN** the webhook receives an inbound message for a conversation that has one or more `pending` scheduled sends
- **THEN** the system SHALL update all pending scheduled sends for that conversation to `status = 'cancelled'` with `cancelled_reason = 'client_replied'` and `cancelled_by_message_id` set to the inbound message ID
- **THEN** the system SHALL broadcast a `scheduled_send_cancelled` WebSocket event for each cancelled send

#### Scenario: Client sends message with no pending scheduled sends
- **WHEN** the webhook receives an inbound message for a conversation with no pending scheduled sends
- **THEN** the system SHALL proceed normally with no cancellation logic

### Requirement: Operator can manually cancel a scheduled send
The system SHALL allow the operator to cancel a pending scheduled send.

#### Scenario: Operator cancels a pending scheduled send
- **WHEN** the operator clicks "Cancelar" on a scheduled send indicator
- **THEN** the system SHALL update the status to `cancelled` with `cancelled_reason = 'operator_cancelled'`
- **THEN** the system SHALL broadcast a `scheduled_send_cancelled` WebSocket event

#### Scenario: Operator tries to cancel an already-sent message
- **WHEN** the operator attempts to cancel a scheduled send that has already been sent
- **THEN** the system SHALL return an error indicating the message was already sent

### Requirement: Display scheduled sends in the UI
The system SHALL show pending scheduled sends in the conversation view and indicate conversations with pending sends in the conversation list.

#### Scenario: Conversation has a pending scheduled send
- **WHEN** the operator opens a conversation with a pending scheduled send
- **THEN** the UI SHALL display a pill/banner showing the scheduled time, a preview of the message content, and a cancel button

#### Scenario: Conversation list with scheduled sends
- **WHEN** a conversation has one or more pending scheduled sends
- **THEN** the conversation list SHALL display a clock icon indicator next to that conversation

#### Scenario: Scheduled send is cancelled or sent
- **WHEN** the WebSocket receives a `scheduled_send_cancelled` or `scheduled_send_completed` event
- **THEN** the UI SHALL remove the scheduled send indicator from the conversation view and update the conversation list indicator

### Requirement: List pending scheduled sends for a conversation
The system SHALL expose an endpoint to retrieve pending scheduled sends for a given conversation.

#### Scenario: Fetch pending scheduled sends
- **WHEN** a client requests pending scheduled sends for a conversation
- **THEN** the system SHALL return all scheduled sends with `status = 'pending'` for that conversation, ordered by `send_at`
