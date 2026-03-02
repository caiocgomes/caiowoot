## ADDED Requirements

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
