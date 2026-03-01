## MODIFIED Requirements

### Requirement: List pending annotations with stats
The GET /review endpoint SHALL include history stats alongside the pending annotations: total validated (OK), total rejected, total promoted to rule. The pending stats SHALL use clear labels: "editadas" for drafts the operator changed, "aceitas" for drafts sent as-is.

#### Scenario: Stats include history counts
- **WHEN** the operator fetches GET /review
- **THEN** the response SHALL include `history_stats` with `total_validated`, `total_rejected`, `total_promoted` counts from already-reviewed annotations

## ADDED Requirements

### Requirement: List reviewed annotations history
The system SHALL provide GET /review/history to list already-reviewed annotations (validated=1), ordered by most recent, with their review outcome (validated, rejected, promoted).

#### Scenario: View review history
- **WHEN** the operator fetches GET /review/history
- **THEN** the response SHALL include annotations with `validated=1`, each annotated with its outcome (ok, rejected, promoted)
- **THEN** results SHALL be ordered by created_at DESC
