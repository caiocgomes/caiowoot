## MODIFIED Requirements

### Requirement: Record edit pairs for learning loop
The system SHALL store each (original draft, final sent message) pair whenever the operator sends a message that originated from an IA draft. This record SHALL include: the customer message that triggered the draft, the original draft text, the final sent text, the attachment filename (if any), and the timestamp.

#### Scenario: Operator edits draft before sending
- **WHEN** the operator modifies the IA draft and sends
- **THEN** the system SHALL store both the original draft and the final version as an edit pair

#### Scenario: Operator sends draft unedited
- **WHEN** the operator sends the IA draft without changes
- **THEN** the system SHALL store the pair with a flag indicating no edit was made (useful for tracking acceptance rate)

#### Scenario: Operator writes message manually (no draft)
- **WHEN** the operator clears the draft and writes a message from scratch, or sends when no draft was available
- **THEN** the system SHALL NOT create an edit pair (no original draft to compare)

#### Scenario: Operator sends message with attachment from draft
- **WHEN** the operator sends a message with an attached file and the message originated from a draft
- **THEN** the edit pair SHALL include `attachment_filename` with the name of the attached file

#### Scenario: Operator sends message without attachment
- **WHEN** the operator sends a message without any attachment
- **THEN** the edit pair SHALL have `attachment_filename` as NULL
