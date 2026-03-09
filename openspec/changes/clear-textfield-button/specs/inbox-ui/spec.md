## ADDED Requirements

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
