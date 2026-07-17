## 1. Playwright e2e Infrastructure

- [x] 1.1 Add playwright and pytest-playwright to pyproject.toml dev dependencies, run `uv sync` and `playwright install chromium` [tests: test_playwright_importable]
- [x] 1.2 Create `tests/e2e/conftest.py` with `live_server` fixture (uvicorn on random port), `seeded_db` fixture (conversation with inbound/outbound/bot messages and drafts), `mobile_page` (390x844) and `desktop_page` (1280x800) viewport fixtures [tests: test_live_server_responds, test_mobile_viewport_size]
- [x] 1.3 Write `tests/e2e/test_infra.py` with smoke tests: import, server responds, page loads, viewport sizes, seeded conversation visible [tests: test_playwright_importable, test_live_server_responds, test_page_loads_index, test_mobile_viewport_size, test_seeded_conversation_in_sidebar]

## 2. Design Tokens Veridian

- [x] 2.1 Write `tests/e2e/test_design_tokens.py` with all token validation tests [tests: test_header_uses_primary_color, test_no_1px_borders_between_sections, test_no_whatsapp_green_in_css, test_inter_font_applied, test_material_symbols_present, test_message_bubble_border_radius, test_send_button_pill_shape, test_ghost_borders_only]
- [x] 2.2 Add Google Fonts links (Inter + Material Symbols Outlined) to `index.html` `<head>` [tests: test_inter_font_applied, test_material_symbols_present]
- [x] 2.3 Rewrite `css/tokens.css`: replace all color variables with Veridian palette, add surface tier variables, update border-radius scale, set Inter as body font [tests: test_header_uses_primary_color, test_no_whatsapp_green_in_css, test_message_bubble_border_radius]
- [x] 2.4 Update `css/base.css`: remove 1px solid borders between sections, apply tonal layering via surface tier backgrounds [tests: test_no_1px_borders_between_sections, test_ghost_borders_only]
- [x] 2.5 Replace emoji/text icons with Material Symbols `<span>` elements in `index.html` and JS files (`drafts.js`, `compose.js`, `messages.js`, `schedule.js`) [tests: test_material_symbols_present]
- [x] 2.6 Update `css/compose.css`: pill-shaped send button, ghost borders on inputs [tests: test_send_button_pill_shape, test_ghost_borders_only]

## 3. Glass AI Messages

- [x] 3.1 Write `tests/e2e/test_glass_ai.py` with glassmorphism and badge tests [tests: test_bot_message_glass_ai_style, test_human_outbound_white_bg, test_copilot_badge_on_bot_message, test_no_badge_on_human_message]
- [x] 3.2 Add `.glass-ai` CSS class to `css/base.css`: `background: rgba(0,107,84,0.04)`, `backdrop-filter: blur(12px)`, `border-radius: var(--radius-3xl)` [tests: test_bot_message_glass_ai_style]
- [x] 3.3 Update `js/ui/messages.js` `appendMessage()`: apply `.glass-ai` class and render Copilot badge for bot messages, white bubble style for human outbound [tests: test_bot_message_glass_ai_style, test_human_outbound_white_bg, test_copilot_badge_on_bot_message, test_no_badge_on_human_message]

## 4. Chat Header Redesign

- [x] 4.1 Write `tests/e2e/test_inbox_ui.py` with header, security banner, and timestamp tests [tests: test_redesigned_header_elements, test_security_banner, test_timestamp_small_muted, test_no_standalone_reescrever_button]
- [x] 4.2 Redesign `#chat-header` in `index.html`: avatar image, contact name (white bold), role badge, action buttons (video/call/more with Material Symbols). Update `css/base.css` for primary bg 95% + backdrop-blur [tests: test_redesigned_header_elements]
- [x] 4.3 Add security banner pill below header in `index.html` with lock icon + "Internal Secure Environment" [tests: test_security_banner]
- [x] 4.4 Update `js/ui/messages.js` timestamp rendering: 10px font, outline color, wide tracking, delivery status suffix [tests: test_timestamp_small_muted]

## 5. Draft Carousel

- [x] 5.1 Write `tests/e2e/test_draft_carousel.py` with carousel, selection, labels, refinement, and regression tests [tests: test_three_draft_cards_in_carousel, test_peek_affordance_mobile, test_draft_selection_primary_bg, test_draft_card_labels, test_refinement_input_visible, test_refinement_triggers_regen_request, test_no_old_instruction_bar]
- [x] 5.2 Update `css/compose.css`: draft cards container with `overflow-x: auto`, `scroll-snap-type: x mandatory`, cards with fixed ~240px width, `scroll-snap-align: start`, `gap: 1rem` [tests: test_three_draft_cards_in_carousel, test_peek_affordance_mobile]
- [x] 5.3 Update `js/ui/drafts.js` `showDrafts()`: render cards as carousel items with approach labels in chip headers, selection changes to primary bg with white text [tests: test_draft_selection_primary_bg, test_draft_card_labels]
- [x] 5.4 Add refinement input between AI message and drafts: input with `psychology_alt` icon + refresh button. Wire to existing `regenerateAll()` with operator_instruction. Remove old `#instruction-bar` [tests: test_refinement_input_visible, test_refinement_triggers_regen_request, test_no_old_instruction_bar]

## 6. Compose Toolbar

- [x] 6.1 Write `tests/e2e/test_compose_toolbar.py` with toolbar visibility, layout, and action tests [tests: test_compose_toolbar_visible, test_toolbar_layout_order, test_formalize_calls_rewrite, test_formalize_noop_empty_textarea, test_translate_calls_rewrite, test_attach_triggers_file_input]
- [x] 6.2 Add toolbar HTML to compose area in `index.html`: Formalize (`edit_note`), Translate (`translate`), Attach (`attach_file`) buttons in `surface-container-low` rounded container. Remove standalone Reescrever and Attach buttons from `#btn-group` [tests: test_compose_toolbar_visible, test_toolbar_layout_order, test_no_standalone_reescrever_button]
- [x] 6.3 Update `js/ui/compose.js`: wire Formalize to `/rewrite` endpoint, Translate to `/rewrite` with translation instruction, Attach to existing file picker [tests: test_formalize_calls_rewrite, test_formalize_noop_empty_textarea, test_translate_calls_rewrite, test_attach_triggers_file_input]
- [x] 6.4 Style compose container with `css/compose.css`: `radius-3xl`, `surface-container-low` bg, textarea with send button inline [tests: test_compose_toolbar_visible]

## 7. Mobile Bottom Navigation

- [x] 7.1 Write `tests/e2e/test_bottom_nav.py` with visibility, tab switching, and safe area tests [tests: test_bottom_nav_visible_mobile, test_bottom_nav_hidden_desktop, test_chat_tab_active_by_default, test_insights_shows_placeholder, test_safe_area_padding_css]
- [x] 7.2 Add bottom nav HTML to `index.html`: three tabs (Chat/Insights/History) with Material Symbols icons, hidden on desktop via CSS media query [tests: test_bottom_nav_visible_mobile, test_bottom_nav_hidden_desktop]
- [x] 7.3 Add bottom nav CSS to `css/mobile.css`: fixed bottom, safe area padding, active/inactive tab colors [tests: test_chat_tab_active_by_default, test_safe_area_padding_css]
- [x] 7.4 Add bottom nav JS: tab switching logic, placeholder "Em breve" for Insights/History, Chat restores conversation view [tests: test_insights_shows_placeholder]

## 8. Responsive Layout Updates

- [x] 8.1 Write `tests/e2e/test_responsive.py` with mobile carousel, compose layout, and bottom nav overlap tests [tests: test_mobile_draft_carousel_compact, test_mobile_compose_stacked, test_content_not_hidden_by_bottom_nav]
- [x] 8.2 Update `css/mobile.css`: mobile draft cards ~200px width in carousel, compose toolbar stacked above textarea, content padding-bottom for bottom nav clearance [tests: test_mobile_draft_carousel_compact, test_mobile_compose_stacked, test_content_not_hidden_by_bottom_nav]

## 9. Context Panel Veridian Styling

- [x] 9.1 Write `tests/e2e/test_context_panel.py` with tonal layering and font tests [tests: test_context_panel_tonal_bg, test_context_panel_inter_font]
- [x] 9.2 Update `css/context-panel.css`: `surface-container-low` background, remove opaque borders, section separation via surface tiers, Inter font [tests: test_context_panel_tonal_bg, test_context_panel_inter_font]

## 10. Sidebar and Other Surfaces Token Update

- [x] 10.1 Update `css/sidebar.css`: apply Veridian tokens (colors, font, borders) to sidebar, conversation list items, active state
- [x] 10.2 Update remaining CSS files (`css/review.css`, `css/campaigns.css`, `css/settings.css`, `css/knowledge.css`, `css/toast.css`) to use new token variables where referenced

## 11. Regression

- [x] 11.1 Run `uv run pytest tests/ --ignore=tests/e2e -v` and verify all existing backend tests pass
- [x] 11.2 Run `uv run pytest tests/e2e/ -v` and verify all new e2e tests pass
