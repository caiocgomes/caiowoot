## ADDED Requirements

### Requirement: Store situation summaries as vector embeddings in ChromaDB
The system SHALL maintain a ChromaDB collection ("situations") that stores embeddings of situation summaries from edit pairs. Each entry SHALL reference the edit_pair ID in the main SQLite database and include metadata for filtering.

#### Scenario: New edit pair indexed
- **WHEN** an edit pair is created with a situation_summary
- **THEN** the situation_summary SHALL be embedded and stored in ChromaDB with metadata: edit_pair_id, was_edited (bool), validated (bool, default false), approach_selected (string)

#### Scenario: ChromaDB index is rebuildable
- **WHEN** the ChromaDB data is deleted or corrupted
- **THEN** the system SHALL be able to rebuild the entire ChromaDB index from situation_summary fields in the SQLite edit_pairs table

### Requirement: Retrieve similar edit pairs by situation similarity
The system SHALL retrieve the K most similar edit pairs by comparing the current situation summary against stored situation summaries in ChromaDB. The system SHALL prioritize validated edit pairs when available.

#### Scenario: Retrieval with validated pairs available
- **WHEN** there are 3+ validated edit pairs in the collection
- **THEN** the system SHALL first search among validated pairs (where={"validated": true})
- **THEN** if fewer than 5 validated results are found, the system SHALL fill remaining slots from non-validated pairs
- **THEN** the total number of retrieved pairs SHALL be at most 5

#### Scenario: Retrieval with no validated pairs
- **WHEN** there are no validated edit pairs
- **THEN** the system SHALL retrieve from all available edit pairs by similarity, limited to 5

#### Scenario: Retrieval with insufficient edit pairs (cold start)
- **WHEN** there are fewer than 5 edit pairs total in the collection
- **THEN** the system SHALL return all available pairs
- **THEN** the draft engine SHALL fall back to current behavior (chronological) if zero pairs are available

### Requirement: Retrieved pairs include strategic annotations in few-shot
The few-shot examples built from retrieved edit pairs SHALL include the strategic annotation alongside the customer message, draft, and final message, providing strategic context for the LLM.

#### Scenario: Few-shot with annotation
- **WHEN** a retrieved edit pair has a strategic_annotation
- **THEN** the few-shot example SHALL include: situation summary, customer message, AI draft, operator's final message, and the strategic annotation explaining the correction or confirmation

#### Scenario: Few-shot without annotation
- **WHEN** a retrieved edit pair has no strategic_annotation (NULL)
- **THEN** the few-shot example SHALL include: situation summary, customer message, AI draft, and operator's final message (without annotation section)
