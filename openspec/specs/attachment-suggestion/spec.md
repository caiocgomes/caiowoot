## ADDED Requirements

### Requirement: Known attachments directory
The system SHALL maintain a directory at `knowledge/attachments/` containing files (PDFs, images) that can be suggested by the draft engine. The filenames in this directory serve as the canonical identifiers for attachments.

#### Scenario: Directory listing
- **WHEN** the draft engine builds the prompt
- **THEN** the system SHALL read the contents of `knowledge/attachments/` and include the filenames in a dedicated prompt section

#### Scenario: Empty directory
- **WHEN** `knowledge/attachments/` contains no files
- **THEN** the system SHALL omit the "Anexos disponíveis" section from the prompt
- **THEN** the draft output SHALL NOT contain `suggested_attachment`

### Requirement: API endpoint to list known attachments
The system SHALL expose `GET /api/attachments` returning a JSON list of filenames available in `knowledge/attachments/`. The endpoint SHALL require authentication.

#### Scenario: List available attachments
- **WHEN** an authenticated request is made to `GET /api/attachments`
- **THEN** the system SHALL return a JSON array of filenames from `knowledge/attachments/`

#### Scenario: Unauthenticated request
- **WHEN** a request without valid session cookie is made to `GET /api/attachments`
- **THEN** the system SHALL return 401

### Requirement: API endpoint to serve known attachment files
The system SHALL expose `GET /api/attachments/<filename>` that serves the file from `knowledge/attachments/`. The endpoint SHALL require authentication and validate that the filename exists.

#### Scenario: Serve existing file
- **WHEN** an authenticated request is made to `GET /api/attachments/handbook-cdo.pdf`
- **AND** `knowledge/attachments/handbook-cdo.pdf` exists
- **THEN** the system SHALL return the file with appropriate content-type header

#### Scenario: File not found
- **WHEN** an authenticated request is made to `GET /api/attachments/nonexistent.pdf`
- **AND** the file does not exist in `knowledge/attachments/`
- **THEN** the system SHALL return 404

#### Scenario: Path traversal attempt
- **WHEN** a request is made with a filename containing `..` or `/`
- **THEN** the system SHALL return 400
