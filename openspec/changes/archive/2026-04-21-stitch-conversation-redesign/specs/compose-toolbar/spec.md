## ADDED Requirements

### Requirement: Compose area includes rich toolbar
The compose area SHALL display a toolbar row above the textarea with action buttons: Formalize (`edit_note` icon), Translate (`translate` icon), and Attach (`attach_file` icon). The toolbar SHALL be inside a rounded container (`--radius-3xl`) with `--surface-container-low` background.

#### Scenario: Toolbar visible when conversation open
- **WHEN** the operator has a conversation open
- **THEN** the compose toolbar SHALL be visible above the textarea with Formalize, Translate, and Attach buttons

#### Scenario: Toolbar layout
- **WHEN** the toolbar renders
- **THEN** Formalize and Translate SHALL be left-aligned with a vertical divider between them, Attach SHALL be right-aligned

### Requirement: Formalize button triggers text rewrite
The Formalize button SHALL send the current textarea content to `POST /conversations/{id}/rewrite` with a formalization instruction. The returned text SHALL replace the textarea content.

#### Scenario: Formalize with text in textarea
- **WHEN** the operator has text in the textarea and clicks Formalize
- **THEN** the system SHALL call the rewrite endpoint and replace textarea content with the formalized version

#### Scenario: Formalize with empty textarea
- **WHEN** the textarea is empty and the operator clicks Formalize
- **THEN** nothing SHALL happen (button is no-op or disabled)

#### Scenario: Loading state during formalize
- **WHEN** the rewrite request is in progress
- **THEN** the Formalize button SHALL show a loading indicator and be disabled

### Requirement: Translate button triggers text translation
The Translate button SHALL send the current textarea content to `POST /conversations/{id}/rewrite` with a translation instruction. Initially, it SHALL translate to English. The returned text SHALL replace the textarea content.

#### Scenario: Translate with text in textarea
- **WHEN** the operator has text in the textarea and clicks Translate
- **THEN** the system SHALL call the rewrite endpoint with translation instruction and replace textarea content

#### Scenario: Translate with empty textarea
- **WHEN** the textarea is empty and the operator clicks Translate
- **THEN** nothing SHALL happen

### Requirement: Attach button opens file picker
The Attach button in the toolbar SHALL trigger the existing file picker (`#attach-file` hidden input). This replaces the current standalone attach button in `#btn-group`.

#### Scenario: Attach opens file dialog
- **WHEN** the operator clicks the Attach button in the toolbar
- **THEN** the system SHALL open the native file picker dialog

#### Scenario: File selected shows attachment bar
- **WHEN** a file is selected via the toolbar Attach button
- **THEN** the `#attachment-bar` SHALL appear showing the filename with a remove button
