## ADDED Requirements

### Requirement: Draft cards display as horizontal carousel
The draft cards container SHALL use `overflow-x: auto` with `scroll-snap-type: x mandatory`. Each card SHALL have fixed width (~240px), `scroll-snap-align: start`, and `--radius-2xl` border radius. Cards SHALL be separated by horizontal spacing (1rem gap).

#### Scenario: Three cards in scrollable row
- **WHEN** 3 draft variations are ready
- **THEN** the draft container SHALL render 3 cards in a horizontal scrollable row with snap behavior

#### Scenario: Peek affordance for off-screen cards
- **WHEN** the viewport is narrow enough that not all 3 cards fit
- **THEN** the last visible card SHALL be partially cut off to indicate more content is available via horizontal scroll

#### Scenario: Snap to card on scroll
- **WHEN** the operator scrolls horizontally in the draft carousel
- **THEN** the scroll SHALL snap to the nearest card edge

### Requirement: Selected draft card has primary background
The currently selected draft card SHALL have `--primary` background with white text. Unselected cards SHALL have white background with subtle border. The selected card SHALL show a checkmark icon in its header.

#### Scenario: Visual selection state
- **WHEN** the operator taps a draft card
- **THEN** that card SHALL change to primary background with `on-primary` (white) text
- **THEN** previously selected card SHALL revert to white background

#### Scenario: Default state is no selection
- **WHEN** drafts first appear
- **THEN** no card SHALL be pre-selected (all white background)

### Requirement: Draft card labels match approach
Each draft card header SHALL display a label indicating its approach style. The labels SHALL use small uppercase text with a subtle background chip. Labels SHALL correspond to the draft approach: first card "Direct & Analytical" (or localized), second "Strategic Pivot", third "Casual Internal".

#### Scenario: Labels rendered on cards
- **WHEN** draft cards render
- **THEN** each card SHALL show its approach label in a chip at the top-left of the card

### Requirement: Inline refinement input for AI outputs
Below the Copilot message and above the draft cards, the system SHALL display an inline refinement input with placeholder "Refine last output (e.g., more technical, emphasize cost...)" and a refresh/regenerate button. This input SHALL replace the current `#instruction-bar` visually but map to the same `operator_instruction` field.

#### Scenario: Refinement input visible after AI response
- **WHEN** a Copilot message and draft cards are displayed
- **THEN** a refinement input with `psychology_alt` icon and refresh button SHALL appear between the message and the drafts

#### Scenario: Refinement triggers regeneration
- **WHEN** the operator types in the refinement input and clicks the refresh button
- **THEN** the system SHALL call `POST /conversations/{id}/regenerate` with `operator_instruction` set to the input text and `draft_index: null`

#### Scenario: Empty refinement input
- **WHEN** the refinement input is empty and the operator clicks refresh
- **THEN** the system SHALL regenerate all drafts without additional instruction
