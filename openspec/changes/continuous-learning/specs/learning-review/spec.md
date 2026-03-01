## ADDED Requirements

### Requirement: API endpoint to list pending annotations for review
The system SHALL expose an API endpoint that returns edit pairs with strategic annotations that have not been validated, ordered by most recent first.

#### Scenario: List unreviewed annotations
- **WHEN** a GET request is made to the review endpoint
- **THEN** the system SHALL return edit pairs where strategic_annotation is not NULL and validated is false
- **THEN** each result SHALL include: edit_pair_id, situation_summary, customer_message, original_draft, final_message, was_edited, strategic_annotation, created_at

#### Scenario: No pending annotations
- **WHEN** all annotations have been validated or no annotations exist
- **THEN** the endpoint SHALL return an empty list

### Requirement: Validate or reject an annotation
The system SHALL allow the operator to validate (confirm) or reject an annotation via API call. Validating an annotation marks it as trusted for prioritized retrieval. Rejecting marks it as reviewed but not trusted.

#### Scenario: Operator validates annotation
- **WHEN** the operator confirms an annotation as correct
- **THEN** the edit pair's validated field SHALL be set to true
- **THEN** the ChromaDB metadata for this pair SHALL be updated with validated=true

#### Scenario: Operator rejects annotation
- **WHEN** the operator marks an annotation as incorrect
- **THEN** the edit pair's validated field SHALL be set to true (reviewed) and a rejected flag SHALL be set to true
- **THEN** the ChromaDB metadata SHALL be updated to exclude this pair from prioritized retrieval

### Requirement: Promote annotation to permanent rule
The system SHALL allow the operator to promote a strategic annotation into a permanent learned rule. When promoting, the operator MAY edit the rule text before saving.

#### Scenario: Promote annotation to rule
- **WHEN** the operator clicks "promote to rule" on an annotation
- **THEN** the system SHALL create a new entry in the learned_rules table with the annotation text (or operator-edited version)
- **THEN** the annotation SHALL be marked as validated
- **THEN** the new rule SHALL be active immediately and included in subsequent draft prompts

#### Scenario: Promote with edited text
- **WHEN** the operator edits the rule text before promoting
- **THEN** the learned rule SHALL contain the operator's edited text, not the original annotation text

### Requirement: Review statistics summary
The review endpoint SHALL include summary statistics to help the operator assess the review queue.

#### Scenario: Statistics returned
- **WHEN** the review list is requested
- **THEN** the response SHALL include: total_pending (unreviewed annotations), total_edited (pairs where was_edited=true among pending), total_confirmed (pairs where was_edited=false among pending)
