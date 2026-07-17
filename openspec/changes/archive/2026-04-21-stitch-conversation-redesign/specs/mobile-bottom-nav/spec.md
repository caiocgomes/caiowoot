## ADDED Requirements

### Requirement: Bottom navigation bar on mobile
Below 768px viewport, the system SHALL display a fixed bottom navigation bar with three tabs: Chat (`chat_bubble` icon, filled when active), Insights (`auto_awesome` icon), and History (`history` icon). The active tab SHALL use `--primary` color, inactive tabs SHALL use `--on-surface` at 30% opacity.

#### Scenario: Bottom nav visible on mobile
- **WHEN** the viewport is below 768px and a conversation is open
- **THEN** a bottom navigation bar SHALL be visible at the bottom of the screen with three tab icons and labels

#### Scenario: Bottom nav hidden on desktop
- **WHEN** the viewport is 768px or wider
- **THEN** the bottom navigation bar SHALL NOT be displayed

#### Scenario: Chat tab is default active
- **WHEN** the conversation view loads on mobile
- **THEN** the Chat tab SHALL be active (primary color, filled icon)

### Requirement: Insights and History tabs show placeholder
The Insights and History tabs SHALL be tappable but display a placeholder state ("Em breve") when selected. They SHALL NOT navigate away from the conversation.

#### Scenario: Tap Insights tab
- **WHEN** the operator taps the Insights tab
- **THEN** the system SHALL show a placeholder message in the main content area
- **THEN** the Insights tab SHALL become active (primary color)

#### Scenario: Tap History tab
- **WHEN** the operator taps the History tab
- **THEN** the system SHALL show a placeholder message in the main content area
- **THEN** the History tab SHALL become active (primary color)

#### Scenario: Return to Chat tab
- **WHEN** the operator taps the Chat tab after viewing a placeholder
- **THEN** the conversation view SHALL be restored

### Requirement: Bottom nav respects iOS safe area
The bottom navigation bar SHALL use `padding-bottom: env(safe-area-inset-bottom)` to avoid overlap with the iOS home indicator on notched devices.

#### Scenario: Safe area padding on iPhone
- **WHEN** the app runs on an iPhone with a home indicator bar
- **THEN** the bottom nav SHALL have additional padding below the tab icons to clear the safe area
