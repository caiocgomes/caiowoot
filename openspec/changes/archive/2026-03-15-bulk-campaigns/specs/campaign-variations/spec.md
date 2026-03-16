## ADDED Requirements

### Requirement: Generate message variations via Claude
The system SHALL generate 8 variations of the operator's base message using Claude Haiku. Variations SHALL differ genuinely in sentence structure, opening/closing, register (formal/informal), emoji usage, paragraph order, and length. Synonym-only substitutions are insufficient.

#### Scenario: Generate variations from base message
- **WHEN** the operator writes a base message and requests variation generation
- **THEN** the system SHALL call Claude Haiku with a prompt instructing genuine diversification
- **THEN** the system SHALL store 8 variations in `campaign_variations` linked to the campaign

#### Scenario: Base message contains placeholders
- **WHEN** the base message contains `{{nome}}` or other placeholders
- **THEN** the generated variations SHALL preserve all placeholders exactly as written

#### Scenario: Variation generation fails
- **WHEN** the Claude API call fails
- **THEN** the system SHALL display an error and allow the operator to retry generation

### Requirement: Operator reviews and approves variations
The system SHALL display all generated variations for the operator to review before the campaign can be started. The operator SHALL be able to edit individual variations.

#### Scenario: Review variations
- **WHEN** variations are generated
- **THEN** the system SHALL display all 8 variations in the campaign detail view for review

#### Scenario: Edit a variation
- **WHEN** the operator edits a variation text
- **THEN** the system SHALL update the stored variation

#### Scenario: Regenerate variations
- **WHEN** the operator is not satisfied with the variations
- **THEN** the operator SHALL be able to regenerate all 8 variations (replacing the existing ones)

### Requirement: Random variation assignment
The system SHALL assign a random variation to each contact at send time. The assignment SHALL aim for roughly equal distribution across all 8 variations.

#### Scenario: Assign variation at send time
- **WHEN** the executor picks the next contact to send to
- **THEN** the system SHALL randomly select a variation, preferring variations that have been used less frequently in this campaign

#### Scenario: Retry uses different variation
- **WHEN** a failed contact is retried
- **THEN** the system SHALL assign a different variation than the one used in the previous attempt
