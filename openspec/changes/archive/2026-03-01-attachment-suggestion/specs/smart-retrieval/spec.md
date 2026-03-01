## MODIFIED Requirements

### Requirement: Retrieved pairs include strategic annotations in few-shot
The few-shot examples built from retrieved edit pairs SHALL include the strategic annotation and attachment information alongside the customer message, draft, and final message, providing strategic context for the LLM.

#### Scenario: Few-shot with annotation and attachment
- **WHEN** a retrieved edit pair has a strategic_annotation and a non-NULL attachment_filename
- **THEN** the few-shot example SHALL include: situation summary, customer message, AI draft, operator's final message, the strategic annotation, and the attachment filename

#### Scenario: Few-shot with annotation without attachment
- **WHEN** a retrieved edit pair has a strategic_annotation and NULL attachment_filename
- **THEN** the few-shot example SHALL include: situation summary, customer message, AI draft, operator's final message, and the strategic annotation (without attachment line)

#### Scenario: Few-shot without annotation
- **WHEN** a retrieved edit pair has no strategic_annotation (NULL)
- **THEN** the few-shot example SHALL include: situation summary, customer message, AI draft, and operator's final message (without annotation section)
