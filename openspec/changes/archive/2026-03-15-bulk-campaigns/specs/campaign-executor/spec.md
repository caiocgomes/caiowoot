## ADDED Requirements

### Requirement: Poll and execute campaign sends
The system SHALL run a background poller every 10 seconds that finds running campaigns with `next_send_at <= now` and sends the next pending contact's message.

#### Scenario: Campaign is due for next send
- **WHEN** the poller finds a campaign with `status = 'running'` and `next_send_at <= now()`
- **THEN** the system SHALL pick the next pending contact, assign a random variation, resolve placeholders (e.g. `{{nome}}`), and send via Evolution API
- **THEN** on success, the system SHALL mark the contact as `sent` with timestamp
- **THEN** the system SHALL compute `next_send_at = now() + random(min_interval, max_interval)` and update the campaign

#### Scenario: Text-only send
- **WHEN** the campaign has no attached image
- **THEN** the system SHALL use `sendText` via Evolution API

#### Scenario: Text with image send
- **WHEN** the campaign has an attached image
- **THEN** the system SHALL recompress the image with random JPEG quality (85-95%) and use `sendMedia` via Evolution API with the text as caption

#### Scenario: Send fails
- **WHEN** the Evolution API returns an error for a contact
- **THEN** the system SHALL mark the contact as `failed` with the error message and increment the consecutive failure counter

#### Scenario: Send succeeds after previous failures
- **WHEN** a send succeeds and the consecutive failure counter is > 0
- **THEN** the system SHALL reset the consecutive failure counter to 0

### Requirement: Auto-pause on suspected block
The system SHALL automatically pause a campaign when 5 consecutive sends fail, indicating a possible Meta block on the WhatsApp session.

#### Scenario: 5 consecutive failures detected
- **WHEN** the consecutive failure counter reaches 5
- **THEN** the system SHALL set campaign status to `blocked` and clear `next_send_at`
- **THEN** the system SHALL broadcast a WebSocket event notifying the operator

#### Scenario: Resume after block
- **WHEN** the operator resumes a `blocked` campaign
- **THEN** the system SHALL reset the consecutive failure counter to 0 and set `next_send_at` to now

### Requirement: Campaign completion detection
The system SHALL detect when all contacts have been processed and mark the campaign as completed.

#### Scenario: All contacts processed
- **WHEN** the poller finds a running campaign with no pending contacts
- **THEN** the system SHALL set campaign status to `completed`

### Requirement: Broadcast campaign progress via WebSocket
The system SHALL broadcast progress updates via WebSocket so the frontend can update in real-time.

#### Scenario: Contact sent successfully
- **WHEN** a contact message is sent successfully
- **THEN** the system SHALL broadcast `campaign_progress` event with `{campaign_id, contact_id, status: "sent", sent_count, failed_count, pending_count}`

#### Scenario: Contact send failed
- **WHEN** a contact message fails
- **THEN** the system SHALL broadcast `campaign_progress` event with `{campaign_id, contact_id, status: "failed", error, sent_count, failed_count, pending_count}`

#### Scenario: Campaign status changed
- **WHEN** a campaign status changes (blocked, completed, paused, running)
- **THEN** the system SHALL broadcast `campaign_status` event with `{campaign_id, status}`

### Requirement: Server restart resilience
The system SHALL resume campaign execution after a server restart without losing state.

#### Scenario: Server restarts with running campaign
- **WHEN** the server starts and there are campaigns with `status = 'running'`
- **THEN** the poller SHALL pick them up on its next iteration based on `next_send_at`
