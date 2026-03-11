## ADDED Requirements

### Requirement: Display active rules in learning tab
The learning tab SHALL display a list of active learned rules below the pending annotations section. Each rule SHALL show its text and allow toggle (on/off) and inline text editing.

#### Scenario: View active rules
- **WHEN** the operator opens the Aprendizado tab
- **THEN** the system SHALL display all learned rules with their active/inactive status

#### Scenario: Toggle rule
- **WHEN** the operator toggles a rule
- **THEN** the system SHALL call PATCH /rules/{id}/toggle and update the UI

#### Scenario: Edit rule text
- **WHEN** the operator edits a rule's text and saves
- **THEN** the system SHALL call PUT /rules/{id} with the new text

### Requirement: Display review history stats
The learning tab SHALL display history stats showing how many annotations have been validated, rejected, and promoted to rules.

#### Scenario: History stats visible
- **WHEN** the operator opens the Aprendizado tab
- **THEN** stats SHALL show counts for validated, rejected, and promoted annotations

### Requirement: Display last responder in conversation list
The conversation list SHALL display the name of the operator who sent the last outbound message in each conversation. The name SHALL appear below the message preview text. Each conversation item SHALL also display visual indicators based on `is_new` and `needs_reply` flags. The API response SHALL include `funnel_product` and `funnel_stage` for each conversation.

#### Scenario: Conversation has outbound messages with sent_by
- **WHEN** the conversation list loads and a conversation has outbound messages with `sent_by` set
- **THEN** the system SHALL display the operator name of the most recent outbound message below the preview

#### Scenario: Conversation has no outbound messages
- **WHEN** the conversation list loads and a conversation has no outbound messages
- **THEN** the system SHALL not display any operator name

#### Scenario: Last outbound message has no sent_by
- **WHEN** the conversation list loads and the most recent outbound message has `sent_by` as NULL (pre-migration message)
- **THEN** the system SHALL not display any operator name for that conversation

#### Scenario: New message indicator
- **WHEN** a conversation has `is_new` = true
- **THEN** the system SHALL display a green dot before the contact name and render the name in bold

#### Scenario: Needs reply indicator
- **WHEN** a conversation has `is_new` = false and `needs_reply` = true
- **THEN** the system SHALL render the contact name in bold (no green dot)

#### Scenario: No pending action
- **WHEN** a conversation has `is_new` = false and `needs_reply` = false
- **THEN** the system SHALL render the contact name in normal weight (no dot, no bold)

#### Scenario: Funnel data in API response
- **WHEN** the conversation list is fetched
- **THEN** each conversation item SHALL include `funnel_product` and `funnel_stage` fields

### Requirement: Rewrite button in compose area
The compose area SHALL include a "Reescrever" button in the `#btn-group`, positioned between the send button and the attach button. The button SHALL be styled distinctly from send (not green) to avoid confusion with the send action.

#### Scenario: Button visibility
- **WHEN** the operator views the compose area of any conversation
- **THEN** a "Reescrever" button SHALL be visible between "Enviar" and the attach button

#### Scenario: Button click triggers rewrite
- **WHEN** the operator has text in the textarea and clicks "Reescrever"
- **THEN** the system SHALL send the textarea content to `POST /conversations/{id}/rewrite` and replace the textarea content with the returned text

#### Scenario: Loading state during rewrite
- **WHEN** the rewrite request is in progress
- **THEN** the button SHALL show a loading indicator (e.g., "Reescrevendo...") and be disabled until the response arrives

#### Scenario: Empty textarea
- **WHEN** the textarea is empty and the operator clicks "Reescrever"
- **THEN** nothing SHALL happen (button disabled or no-op)

#### Scenario: Error handling
- **WHEN** the rewrite request fails
- **THEN** the system SHALL show an error alert and keep the original text in the textarea unchanged

### Requirement: Clear button in compose textarea
The compose area SHALL include a clear button that removes all text from the textarea and resets draft selection state. The button SHALL only be visible when the textarea contains text.

#### Scenario: Button visibility with text
- **WHEN** the textarea contains text (from draft selection or manual typing)
- **THEN** a clear button (X icon) SHALL be visible near the textarea

#### Scenario: Button visibility without text
- **WHEN** the textarea is empty
- **THEN** the clear button SHALL be hidden

#### Scenario: Clearing text and draft state
- **WHEN** the operator taps the clear button
- **THEN** the textarea SHALL be emptied
- **THEN** the selected draft state SHALL be reset (currentDraftId, currentDraftGroupId, selectedDraftIndex)
- **THEN** the justification display SHALL be hidden

#### Scenario: Clear button on mobile
- **WHEN** the operator is on a mobile device
- **THEN** the clear button SHALL have a touch-friendly tap target (minimum 44x44px)
