## ADDED Requirements

### Requirement: Cache shared prompt prefix across draft generation calls
The system SHALL use Anthropic prompt caching (`cache_control: {"type": "ephemeral"}`) on the shared prefix of the system prompt when generating draft variations, so that the 2nd and 3rd parallel calls reuse the cached prefix instead of reprocessing it.

#### Scenario: Three draft calls share cached system prefix
- **WHEN** the draft engine generates 3 draft variations in parallel
- **THEN** the system prompt SHALL be sent as a list of two content blocks
- **THEN** the first block SHALL contain the base system prompt, learned rules section, and knowledge base content, with `cache_control: {"type": "ephemeral"}`
- **THEN** the second block SHALL contain only the approach modifier text, without `cache_control`

#### Scenario: Cache hit on subsequent calls
- **WHEN** the 2nd or 3rd draft call is made within the same batch (or within 5 minutes for cross-conversation)
- **THEN** `response.usage.cache_read_input_tokens` SHALL be greater than 0

#### Scenario: Cache write on first call
- **WHEN** the first draft call of a batch executes (no existing cache)
- **THEN** `response.usage.cache_creation_input_tokens` SHALL be greater than 0

### Requirement: Log cache performance metrics
The system SHALL log cache hit/miss metrics after each draft generation call for observability.

#### Scenario: Cache metrics logged after each call
- **WHEN** a draft generation API call completes
- **THEN** the system SHALL log `cache_read_input_tokens` and `cache_creation_input_tokens` from `response.usage` at INFO level
