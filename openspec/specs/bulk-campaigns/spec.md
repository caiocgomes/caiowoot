## ADDED Requirements

### Requirement: Create a campaign from CSV upload
The system SHALL allow the operator to create a campaign by uploading a CSV file with contacts and providing a base message. The CSV SHALL contain at minimum `telefone` and `nome` columns. The system SHALL parse the CSV, validate phone numbers, and create the campaign in `draft` status.

#### Scenario: Valid CSV uploaded
- **WHEN** the operator uploads a CSV with valid `telefone` and `nome` columns and provides a campaign name
- **THEN** the system SHALL create a campaign record with `status = 'draft'` and create `campaign_contacts` records for each row with `status = 'pending'`

#### Scenario: CSV with invalid or missing columns
- **WHEN** the operator uploads a CSV without `telefone` column
- **THEN** the system SHALL return an error indicating the required columns

#### Scenario: CSV with duplicate phone numbers
- **WHEN** the operator uploads a CSV with duplicate phone numbers
- **THEN** the system SHALL deduplicate and keep only one entry per phone number

### Requirement: Configure campaign timing
The system SHALL allow the operator to set minimum and maximum interval in seconds for randomized timing between sends. Default values SHALL be 60s minimum and 180s maximum.

#### Scenario: Operator sets custom interval
- **WHEN** the operator configures min_interval=90 and max_interval=240
- **THEN** the system SHALL store these values and use them for randomized delay between sends

#### Scenario: Operator uses default interval
- **WHEN** the operator does not configure intervals
- **THEN** the system SHALL use 60s minimum and 180s maximum

### Requirement: Attach optional image to campaign
The system SHALL allow the operator to attach a single image to the campaign. The image SHALL be sent along with the text variation to each contact.

#### Scenario: Campaign with image
- **WHEN** the operator attaches an image during campaign creation
- **THEN** the system SHALL store the image and send it with each message, applying slight JPEG recompression (quality 85-95%, randomized) to vary the file hash per send

#### Scenario: Campaign without image
- **WHEN** the operator does not attach an image
- **THEN** the system SHALL send text-only messages

### Requirement: Campaign lifecycle management
The system SHALL support campaign states: `draft`, `running`, `paused`, `blocked`, `completed`. The operator SHALL be able to start, pause, resume, and retry campaigns.

#### Scenario: Start a draft campaign
- **WHEN** the operator clicks "Iniciar" on a campaign with status `draft` that has approved variations
- **THEN** the system SHALL set status to `running` and set `next_send_at` to now

#### Scenario: Pause a running campaign
- **WHEN** the operator clicks "Pausar" on a running campaign
- **THEN** the system SHALL set status to `paused` and clear `next_send_at`

#### Scenario: Resume a paused or blocked campaign
- **WHEN** the operator clicks "Retomar" on a paused or blocked campaign
- **THEN** the system SHALL set status to `running` and set `next_send_at` to now
- **THEN** the system SHALL continue sending from the next pending contact (not restart from beginning)

#### Scenario: Campaign completes
- **WHEN** all contacts in the campaign have status `sent` or `failed`
- **THEN** the system SHALL set campaign status to `completed`

### Requirement: Retry failed contacts
The system SHALL allow the operator to retry all failed contacts in a campaign. Retry SHALL use a new random variation and new random timing.

#### Scenario: Retry all failed
- **WHEN** the operator clicks "Reenviar falhos" on a campaign with failed contacts
- **THEN** the system SHALL reset all `failed` contacts to `pending` and set campaign status to `running`
- **THEN** each retried contact SHALL receive a different variation than the one that failed

### Requirement: Campaign list and detail UI
The system SHALL display a "Campanhas" tab in the sidebar listing all campaigns. Selecting a campaign SHALL show its detail in the main area with status counts, contact list, and controls.

#### Scenario: View campaign list
- **WHEN** the operator switches to the "Campanhas" tab
- **THEN** the system SHALL display all campaigns ordered by creation date (newest first) with name, status, and sent/total counts

#### Scenario: View campaign detail
- **WHEN** the operator selects a campaign from the list
- **THEN** the system SHALL display: campaign name, status, progress bar, counts (sent/failed/pending), contact list with individual status, variation list, timing configuration, and action buttons (start/pause/resume/retry)

#### Scenario: View contact detail in campaign
- **WHEN** the operator views the contact list in a campaign
- **THEN** each contact SHALL show: phone number, name, status (sent/failed/pending), and timestamp of last send attempt
