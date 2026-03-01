## ADDED Requirements

### Requirement: Store course documentation as knowledge base
The system SHALL maintain a knowledge base directory containing markdown files with course information. Each course SHALL have a file with: course name, description, target audience, format, duration, price, syllabus summary, and key differentiators. The system SHALL load these files at startup and include their content in the draft engine prompts.

#### Scenario: Knowledge base loaded at startup
- **WHEN** the application starts
- **THEN** all markdown files in the knowledge base directory SHALL be loaded into memory
- **THEN** their content SHALL be available to the draft engine for prompt construction

#### Scenario: Knowledge base file updated
- **WHEN** a knowledge base file is modified on disk
- **THEN** the system SHALL pick up the change on the next draft generation (reload on each request, or watch for changes)

### Requirement: Include sales playbook in knowledge base
The knowledge base SHALL include a sales playbook document with: common objections and recommended handling strategies, qualifying questions for different lead profiles, comparison frameworks (vs MBA, vs bootcamps, vs free content), and pricing anchoring strategies (daily cost, ROI, payback period).

#### Scenario: Playbook informs draft generation
- **WHEN** the draft engine generates a response
- **THEN** the sales playbook content SHALL be included in the system prompt alongside course documentation

### Requirement: Inline knowledge base without RAG
The knowledge base SHALL be included directly in the LLM prompt (inline), without a vector database or embedding-based retrieval. The total knowledge base content SHALL fit within the Claude API context window alongside conversation history and few-shot examples.

#### Scenario: All content fits in context
- **WHEN** the draft engine constructs a prompt
- **THEN** the full knowledge base, conversation history (up to reasonable limit), and few-shot examples SHALL fit within the model's context window
- **THEN** if the total exceeds limits, conversation history SHALL be truncated (oldest messages first) before knowledge base content
