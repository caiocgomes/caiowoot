## MODIFIED Requirements

### Requirement: Generate strategic annotation after message send
The system SHALL generate a strategic annotation asynchronously (background task) after each message is sent by the operator. The annotation SHALL analyze the diff between the selected draft and the final message, including attachment behavior, to extract the strategic reasoning behind the edit.

#### Scenario: Annotation for edited message
- **WHEN** the operator edits a draft before sending (was_edited=true)
- **THEN** a background Haiku call SHALL analyze the customer message, the original draft, the final message, and the attachment filename (if any), and produce a structured annotation containing: (1) what the AI proposed, (2) what the operator changed, (3) the inferred strategic reason for the change
- **THEN** the annotation SHALL be stored in the edit pair record

#### Scenario: Annotation for accepted message (no edit)
- **WHEN** the operator sends a draft without editing (was_edited=false)
- **THEN** the annotation SHALL record a confirmation: what approach was used and that it was validated by acceptance
- **THEN** the annotation SHALL be stored in the edit pair record

#### Scenario: Annotation for message with attachment
- **WHEN** the operator sends a message with an attachment
- **THEN** the annotation analysis SHALL include the fact that an attachment was sent and which file it was
- **THEN** the annotation SHALL capture the strategic reasoning for sending the attachment (e.g., "operador enviou handbook do CDO quando cliente confirmou interesse no programa")

#### Scenario: Annotation for message without attachment when AI suggested one
- **WHEN** the operator sends a message without attachment but the draft had a `suggested_attachment`
- **THEN** the annotation SHALL note that the operator chose not to send the suggested attachment

#### Scenario: Annotation generated asynchronously
- **WHEN** the operator sends a message
- **THEN** the annotation generation SHALL NOT block the send flow
- **THEN** the annotation SHALL be written to the edit pair record when ready (may be seconds after the send completes)

### Requirement: Annotation captures strategic intent, not style
The annotation SHALL focus on the strategic decision (qualify vs. recommend, address objection vs. ignore, push vs. pull back, attach vs. not attach) rather than textual style differences (shorter sentences, different emoji usage, word choice).

#### Scenario: Strategic correction identified
- **WHEN** the AI draft recommended a course directly but the operator changed to a qualifying question
- **THEN** the annotation SHALL describe the strategic correction (e.g., "IA recomendou curso direto. Operador voltou para qualificação. Situação: interesse vago sem contexto do perfil do cliente.")

#### Scenario: Style-only edit not over-interpreted
- **WHEN** the operator makes minor text adjustments (shortening, rephrasing) without changing the strategic approach
- **THEN** the annotation SHALL note the approach was confirmed and edits were stylistic, not strategic

#### Scenario: Attachment decision captured
- **WHEN** the operator sends an attachment that the AI did not suggest
- **THEN** the annotation SHALL describe the attachment decision as a strategic action (e.g., "operador anexou handbook do CDO para reforçar a proposta de valor")

### Requirement: Annotation failure does not affect system operation
The annotation is a non-critical enhancement. If the Haiku call fails or times out, the system SHALL log the error and continue without annotation. The edit pair remains valid without an annotation.

#### Scenario: Annotation call fails
- **WHEN** the Haiku call for annotation generation fails
- **THEN** the system SHALL log the error
- **THEN** the edit pair strategic_annotation field SHALL remain NULL
- **THEN** no error is shown to the operator
