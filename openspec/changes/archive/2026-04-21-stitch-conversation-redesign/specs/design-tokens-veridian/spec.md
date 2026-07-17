## ADDED Requirements

### Requirement: Veridian color tokens replace current palette
The system SHALL define CSS custom properties for all Veridian Copilot colors in `tokens.css`. The primary color SHALL be `#006B54` (Authority Green), secondary SHALL be `#4648d4` (Intelligence Indigo), and tertiary SHALL be `#005212` (Success Green). All surface tiers SHALL be defined: `--surface` (#f8f9fa), `--surface-container-low` (#f3f4f5), `--surface-container` (#edeeef), `--surface-container-high` (#e7e8e9), `--surface-container-highest` (#e1e3e4), `--surface-container-lowest` (#ffffff).

#### Scenario: Primary color applied to header and CTAs
- **WHEN** the conversation view renders
- **THEN** the chat header background SHALL use `--primary` (#006B54) and primary action buttons SHALL use `--primary` as background

#### Scenario: Surface tiers used for layering
- **WHEN** sections of the UI need visual separation
- **THEN** the system SHALL use different `--surface-*` tiers instead of borders

#### Scenario: Old WhatsApp green removed
- **WHEN** the tokens are loaded
- **THEN** no element SHALL use `#25D366` or the old primary color

### Requirement: Inter font family via Google Fonts
The system SHALL load Inter font (weights 300-800) from Google Fonts CDN with `display=swap`. The body, headings, labels, and all UI text SHALL use Inter as the primary font family.

#### Scenario: Font loaded and applied
- **WHEN** the page loads
- **THEN** all text elements SHALL render in Inter font family
- **THEN** the Google Fonts link SHALL include `?family=Inter:wght@300;400;500;600;700;800&display=swap`

#### Scenario: Fallback during load
- **WHEN** Inter has not yet loaded (FOUT period)
- **THEN** system fonts SHALL display as fallback until swap completes

### Requirement: Material Symbols Outlined icons
The system SHALL load Material Symbols Outlined from Google Fonts CDN. Icons SHALL be rendered as `<span class="material-symbols-outlined">icon_name</span>`. Existing emoji and text-based icons SHALL be replaced with Material Symbols equivalents.

#### Scenario: Icons render correctly
- **WHEN** the conversation view loads
- **THEN** all action buttons (send, attach, refresh, back) SHALL display Material Symbols icons instead of emoji or text

#### Scenario: Icon font loaded
- **WHEN** the page loads
- **THEN** the Material Symbols Outlined font SHALL be available via CDN link

### Requirement: Border radius scale follows Veridian system
The system SHALL use the following border-radius scale: `--radius-default` (0.25rem), `--radius-lg` (0.5rem), `--radius-xl` (0.75rem), `--radius-2xl` (1rem), `--radius-3xl` (1.5rem), `--radius-full` (9999px). Message bubbles SHALL use `--radius-2xl`. Draft cards SHALL use `--radius-3xl`. Primary action buttons SHALL use `--radius-full`.

#### Scenario: Message bubbles have correct radius
- **WHEN** a message bubble renders
- **THEN** its border-radius SHALL be `--radius-2xl` (1rem)

#### Scenario: Buttons have pill shape
- **WHEN** a primary action button renders
- **THEN** its border-radius SHALL be `--radius-full` (9999px)

### Requirement: No-line rule enforced
The system SHALL NOT use `border: 1px solid` for visual section separation. Boundaries SHALL be defined by background color shifts between surface tiers or by whitespace. Ghost borders (outline-variant at 20% opacity) SHALL be used only when accessibility requires a visible boundary.

#### Scenario: No opaque borders between sections
- **WHEN** the conversation view renders
- **THEN** no section divider SHALL use a fully opaque 1px border

#### Scenario: Ghost border for accessible boundaries
- **WHEN** an input field or interactive element needs a visible boundary
- **THEN** the border SHALL use `--outline-variant` at 20% opacity maximum
