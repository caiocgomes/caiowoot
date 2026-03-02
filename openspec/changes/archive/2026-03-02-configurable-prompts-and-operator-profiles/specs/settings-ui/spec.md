## ADDED Requirements

### Requirement: Settings button in main interface
The system SHALL display a settings button (gear icon) in the main interface header that opens the settings modal.

#### Scenario: Settings button visible to all operators
- **WHEN** an authenticated operator views the main interface
- **THEN** a settings button SHALL be visible in the header area

#### Scenario: Click settings button
- **WHEN** the operator clicks the settings button
- **THEN** a modal/overlay SHALL open showing the settings interface

### Requirement: Settings modal with tabbed interface
The settings modal SHALL have two tabs: "Prompts" and "Meu Perfil".

#### Scenario: Admin opens settings
- **WHEN** an admin operator opens the settings modal
- **THEN** both tabs SHALL be visible: "Prompts" and "Meu Perfil"
- **THEN** the "Prompts" tab SHALL be the default active tab

#### Scenario: Non-admin opens settings
- **WHEN** a non-admin operator opens the settings modal
- **THEN** only the "Meu Perfil" tab SHALL be visible
- **THEN** the "Prompts" tab SHALL be hidden

### Requirement: Prompts tab shows editable prompt sections
The Prompts tab SHALL display a textarea for each editable prompt section with a label and a "Restaurar padrão" (reset) button.

#### Scenario: Load prompts tab
- **WHEN** the admin opens the Prompts tab
- **THEN** the system SHALL fetch GET /api/settings/prompts and populate each textarea with the current value
- **THEN** the sections displayed SHALL be: Postura, Tom, Regras, Variação Direta, Variação Consultiva, Variação Casual, Prompt de Resumo, Prompt de Anotação

#### Scenario: Save prompts
- **WHEN** the admin edits one or more textareas and clicks "Salvar"
- **THEN** the system SHALL send PUT /api/settings/prompts with the changed values
- **THEN** a success confirmation SHALL be displayed

#### Scenario: Reset individual prompt to default
- **WHEN** the admin clicks "Restaurar padrão" next to a prompt section
- **THEN** the system SHALL send that key as null in PUT /api/settings/prompts
- **THEN** the textarea SHALL be repopulated with the hardcoded default value

### Requirement: Profile tab shows operator profile form
The Profile tab SHALL display the operator's display_name and context fields.

#### Scenario: Load profile tab
- **WHEN** the operator opens the "Meu Perfil" tab
- **THEN** the system SHALL fetch GET /api/settings/profile and populate the form
- **THEN** the form SHALL contain: a text input for display_name and a textarea for context

#### Scenario: Save profile
- **WHEN** the operator edits their profile and clicks "Salvar"
- **THEN** the system SHALL send PUT /api/settings/profile with the form values
- **THEN** a success confirmation SHALL be displayed

#### Scenario: Context textarea has guidance placeholder
- **WHEN** the context textarea is empty
- **THEN** it SHALL show placeholder text explaining what to write (e.g., "Descreva quem você é em relação ao negócio, o que a IA deve saber sobre você, o que pode ou não fazer...")
