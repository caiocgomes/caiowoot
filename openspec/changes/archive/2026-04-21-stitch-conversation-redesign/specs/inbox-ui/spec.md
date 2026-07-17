## MODIFIED Requirements

### Requirement: Rewrite button in compose area
The compose area SHALL include a "Reescrever" button in the `#btn-group`, positioned between the send button and the attach button. The button SHALL be styled distinctly from send (not green) to avoid confusion with the send action. **CHANGE:** The standalone Reescrever button is removed from `#btn-group`. Its functionality is replaced by the Formalize button in the new compose toolbar (see `compose-toolbar` spec). The Attach button also moves to the toolbar.

#### Scenario: Button visibility
- **WHEN** the operator views the compose area of any conversation
- **THEN** the Formalize action SHALL be available in the compose toolbar above the textarea
- **THEN** no standalone "Reescrever" button SHALL exist in `#btn-group`

#### Scenario: Button click triggers rewrite
- **WHEN** the operator has text in the textarea and clicks Formalize in the toolbar
- **THEN** the system SHALL send the textarea content to `POST /conversations/{id}/rewrite` and replace the textarea content with the returned text

#### Scenario: Loading state during rewrite
- **WHEN** the rewrite request is in progress
- **THEN** the Formalize button SHALL show a loading indicator and be disabled until the response arrives

#### Scenario: Empty textarea
- **WHEN** the textarea is empty and the operator clicks Formalize
- **THEN** nothing SHALL happen (button disabled or no-op)

#### Scenario: Error handling
- **WHEN** the rewrite request fails
- **THEN** the system SHALL show an error toast and keep the original text in the textarea unchanged

## ADDED Requirements

### Requirement: Chat header redesigned with avatar and badge
The chat header SHALL display the contact's avatar (circular, with white/20 border), the contact name in bold white text, and a subtitle badge showing the contact's role or label (e.g., "CaioWoot Executive") in small uppercase text. The header SHALL use `--primary` background with 95% opacity and `backdrop-filter: blur`.

#### Scenario: Header with contact info
- **WHEN** the operator opens a conversation
- **THEN** the chat header SHALL show the contact avatar, name, and role badge on the left, with action buttons (video, call, more) on the right

#### Scenario: Header styling
- **WHEN** the header renders
- **THEN** the background SHALL be `--primary` at 95% opacity with backdrop blur
- **THEN** the contact name SHALL be white, bold, lg size
- **THEN** the role badge SHALL be small uppercase text in `--primary-fixed-dim` at 70% opacity

### Requirement: Security banner below header
A small centered pill SHALL appear below the chat header showing a lock icon and "Internal Secure Environment" text in uppercase, using `--primary` color at 5% background opacity.

#### Scenario: Banner visible in conversation
- **WHEN** the operator views a conversation
- **THEN** a security pill SHALL be visible below the header with lock icon and text

### Requirement: Message timestamps use Veridian styling
Message timestamps SHALL be displayed in 10px font, `--outline` color, medium weight, with wide tracking. Format SHALL include time and delivery status (e.g., "10:42 AM . SENT", "10:43 AM . DELIVERED").

#### Scenario: Timestamp styling
- **WHEN** a message renders
- **THEN** the timestamp SHALL appear below the bubble in small, muted text with delivery status
