## ADDED Requirements

### Requirement: AI messages render with glass-ai effect
Messages sent by the AI/bot SHALL render with a distinct visual style: semi-transparent primary background (`rgba(0, 107, 84, 0.04)`), `backdrop-filter: blur(12px)`, and `--radius-3xl` border radius. Human outbound messages SHALL render with white background, subtle shadow, and `--radius-2xl` border radius.

#### Scenario: Bot message has glassmorphism
- **WHEN** a message with `msg.bot === true` or `msg.direction === "outbound" && msg.sent_by === "bot"` is rendered
- **THEN** the message bubble SHALL have class `glass-ai` with the glassmorphism styles applied

#### Scenario: Human outbound message style
- **WHEN** a human-sent outbound message is rendered
- **THEN** the message bubble SHALL have white background, `box-shadow: 0 1px 2px rgba(0,0,0,0.05)`, and `border: 1px solid rgba(0,0,0,0.05)`

#### Scenario: Inbound message style
- **WHEN** an inbound (customer) message is rendered
- **THEN** the message bubble SHALL maintain left-alignment with appropriate contrast background

### Requirement: AI messages display Copilot badge
AI-generated messages SHALL display a badge above the message bubble with the Veridian Copilot icon (`auto_awesome` filled) and label "Veridian Copilot" in uppercase, small text, primary color.

#### Scenario: Badge visible on bot messages
- **WHEN** a bot message renders in the conversation
- **THEN** a badge with a green circle icon (`auto_awesome`) and text "Veridian Copilot" SHALL appear above the message bubble

#### Scenario: Badge not shown on human messages
- **WHEN** a human-sent message renders
- **THEN** no Copilot badge SHALL be displayed

### Requirement: AI messages can show verification indicator
AI messages SHALL optionally display a verification indicator (checkmark icon + "Strategy Alignment Verified" text) at the bottom of the message bubble when the draft was verified/classified.

#### Scenario: Verification shown when classification exists
- **WHEN** a bot message has associated classification data (funnel_product and funnel_stage are set)
- **THEN** a subtle verification line SHALL appear at the bottom of the bubble with `verified` icon and label

#### Scenario: No verification when unclassified
- **WHEN** a bot message has no associated classification
- **THEN** no verification indicator SHALL appear
