## Test Strategy

**Framework:** Playwright + pytest-playwright (Chromium headless)
**Localização:** `tests/e2e/`
**Execução:** `uv run pytest tests/e2e/ -v`
**Fixtures:**
- `live_server`: sobe FastAPI com uvicorn em porta aleatória, yield base URL
- `page`: Chromium headless via pytest-playwright, navega para live_server
- `mobile_page`: viewport 390x844 (iPhone 14)
- `desktop_page`: viewport 1280x800
- `seeded_db`: banco populado com conversa contendo mensagens inbound, outbound humanas, outbound bot, e drafts pendentes

**Convenções:** async tests, `expect` do Playwright para assertions, `evaluate` para computed styles. Backend tests existentes (`tests/`) não são alterados.

## Spec-to-Test Mapping

### Capability: e2e-playwright-infra

#### Scenario: Dependencies installed
- **Test type**: integration
- **Test file**: `tests/e2e/test_infra.py`
- **Test name**: `test_playwright_importable`
- **Setup (GIVEN)**: Environment com deps instaladas
- **Action (WHEN)**: `import playwright`
- **Assert (THEN)**: Import não levanta exceção

#### Scenario: Server starts before tests
- **Test type**: integration
- **Test file**: `tests/e2e/test_infra.py`
- **Test name**: `test_live_server_responds`
- **Setup (GIVEN)**: Fixture `live_server` ativa
- **Action (WHEN)**: GET request para base URL
- **Assert (THEN)**: Status 200

#### Scenario: Page navigates to app
- **Test type**: e2e
- **Test file**: `tests/e2e/test_infra.py`
- **Test name**: `test_page_loads_index`
- **Setup (GIVEN)**: `live_server` + `page`
- **Action (WHEN)**: `page.goto("/")`
- **Assert (THEN)**: Title contém "CaioWoot" ou sidebar visível

#### Scenario: Mobile viewport
- **Test type**: e2e
- **Test file**: `tests/e2e/test_infra.py`
- **Test name**: `test_mobile_viewport_size`
- **Setup (GIVEN)**: `mobile_page`
- **Action (WHEN)**: `page.viewport_size`
- **Assert (THEN)**: width=390, height=844

#### Scenario: Seeded conversation available
- **Test type**: e2e
- **Test file**: `tests/e2e/test_infra.py`
- **Test name**: `test_seeded_conversation_in_sidebar`
- **Setup (GIVEN)**: `live_server` com `seeded_db`
- **Action (WHEN)**: `page.goto("/")`
- **Assert (THEN)**: Pelo menos um `.conv-item` visível no sidebar

### Capability: design-tokens-veridian

#### Scenario: Primary color applied to header and CTAs
- **Test type**: e2e
- **Test file**: `tests/e2e/test_design_tokens.py`
- **Test name**: `test_header_uses_primary_color`
- **Setup (GIVEN)**: Conversa aberta no `desktop_page`
- **Action (WHEN)**: Avaliar computed background-color do `#chat-header` ou `header`
- **Assert (THEN)**: Background contém rgb equivalente a `#006B54` (0, 107, 84)

#### Scenario: Surface tiers used for layering
- **Test type**: e2e
- **Test file**: `tests/e2e/test_design_tokens.py`
- **Test name**: `test_no_1px_borders_between_sections`
- **Setup (GIVEN)**: Conversa aberta no `desktop_page`
- **Action (WHEN)**: Avaliar computed border das seções principais (#compose, #messages, #context-panel)
- **Assert (THEN)**: Nenhuma seção tem `border-width: 1px` com `border-style: solid` e opacity > 0.2

#### Scenario: Old WhatsApp green removed
- **Test type**: e2e
- **Test file**: `tests/e2e/test_design_tokens.py`
- **Test name**: `test_no_whatsapp_green_in_css`
- **Setup (GIVEN)**: App carregado
- **Action (WHEN)**: Buscar `#25D366` nos stylesheets via `document.styleSheets`
- **Assert (THEN)**: Nenhuma regra CSS contém `#25D366` ou `rgb(37, 211, 102)`

#### Scenario: Font loaded and applied
- **Test type**: e2e
- **Test file**: `tests/e2e/test_design_tokens.py`
- **Test name**: `test_inter_font_applied`
- **Setup (GIVEN)**: App carregado
- **Action (WHEN)**: Avaliar `getComputedStyle(document.body).fontFamily`
- **Assert (THEN)**: Contém "Inter"

#### Scenario: Icons render correctly
- **Test type**: e2e
- **Test file**: `tests/e2e/test_design_tokens.py`
- **Test name**: `test_material_symbols_present`
- **Setup (GIVEN)**: Conversa aberta
- **Action (WHEN)**: Localizar `.material-symbols-outlined` no DOM
- **Assert (THEN)**: Pelo menos 3 elementos com essa classe visíveis

#### Scenario: Message bubbles have correct radius
- **Test type**: e2e
- **Test file**: `tests/e2e/test_design_tokens.py`
- **Test name**: `test_message_bubble_border_radius`
- **Setup (GIVEN)**: Conversa com mensagens
- **Action (WHEN)**: Avaliar computed `border-radius` de uma `.msg` bubble
- **Assert (THEN)**: Border-radius = 16px (1rem)

#### Scenario: Buttons have pill shape
- **Test type**: e2e
- **Test file**: `tests/e2e/test_design_tokens.py`
- **Test name**: `test_send_button_pill_shape`
- **Setup (GIVEN)**: Compose area visível
- **Action (WHEN)**: Avaliar computed `border-radius` do botão send
- **Assert (THEN)**: Border-radius >= 9999px ou valor alto indicando pill

#### Scenario: No opaque borders between sections
- **Test type**: e2e
- **Test file**: `tests/e2e/test_design_tokens.py`
- **Test name**: `test_ghost_borders_only`
- **Setup (GIVEN)**: App carregado
- **Action (WHEN)**: Avaliar inputs e elementos interativos focados
- **Assert (THEN)**: Borders visíveis usam opacity <= 0.2 (via rgba ou outline-variant)

### Capability: glass-ai-messages

#### Scenario: Bot message has glassmorphism
- **Test type**: e2e
- **Test file**: `tests/e2e/test_glass_ai.py`
- **Test name**: `test_bot_message_glass_ai_style`
- **Setup (GIVEN)**: Conversa com mensagem bot no `desktop_page`
- **Action (WHEN)**: Localizar mensagem bot, avaliar computed styles
- **Assert (THEN)**: Background contém `rgba` com 0.04 alpha, `backdrop-filter` contém "blur"

#### Scenario: Human outbound message style
- **Test type**: e2e
- **Test file**: `tests/e2e/test_glass_ai.py`
- **Test name**: `test_human_outbound_white_bg`
- **Setup (GIVEN)**: Conversa com mensagem outbound humana
- **Action (WHEN)**: Localizar mensagem outbound não-bot, avaliar computed styles
- **Assert (THEN)**: Background branco (rgb 255,255,255), sem classe `glass-ai`

#### Scenario: Badge visible on bot messages
- **Test type**: e2e
- **Test file**: `tests/e2e/test_glass_ai.py`
- **Test name**: `test_copilot_badge_on_bot_message`
- **Setup (GIVEN)**: Conversa com mensagem bot
- **Action (WHEN)**: Localizar elemento com texto "Veridian Copilot" próximo à mensagem bot
- **Assert (THEN)**: Badge visível com ícone `auto_awesome`

#### Scenario: Badge not shown on human messages
- **Test type**: e2e
- **Test file**: `tests/e2e/test_glass_ai.py`
- **Test name**: `test_no_badge_on_human_message`
- **Setup (GIVEN)**: Conversa com mensagens humanas
- **Action (WHEN)**: Verificar ausência de badge Copilot em mensagens outbound humanas
- **Assert (THEN)**: Nenhum elemento "Veridian Copilot" associado a mensagens humanas

### Capability: draft-carousel

#### Scenario: Three cards in scrollable row
- **Test type**: e2e
- **Test file**: `tests/e2e/test_draft_carousel.py`
- **Test name**: `test_three_draft_cards_in_carousel`
- **Setup (GIVEN)**: Conversa com drafts pendentes
- **Action (WHEN)**: Contar `.draft-card` no container
- **Assert (THEN)**: 3 cards visíveis, container tem `overflow-x: auto` e `scroll-snap-type` contém "x"

#### Scenario: Peek affordance for off-screen cards
- **Test type**: e2e
- **Test file**: `tests/e2e/test_draft_carousel.py`
- **Test name**: `test_peek_affordance_mobile`
- **Setup (GIVEN)**: `mobile_page` com drafts
- **Action (WHEN)**: Verificar se container de drafts tem scroll width > client width
- **Assert (THEN)**: `scrollWidth > clientWidth` (indica conteúdo além da viewport)

#### Scenario: Visual selection state
- **Test type**: e2e
- **Test file**: `tests/e2e/test_draft_carousel.py`
- **Test name**: `test_draft_selection_primary_bg`
- **Setup (GIVEN)**: 3 drafts visíveis
- **Action (WHEN)**: Click no segundo draft card
- **Assert (THEN)**: Segundo card tem background = primary (#006B54), texto branco; primeiro e terceiro têm background branco

#### Scenario: Labels rendered on cards
- **Test type**: e2e
- **Test file**: `tests/e2e/test_draft_carousel.py`
- **Test name**: `test_draft_card_labels`
- **Setup (GIVEN)**: Drafts visíveis
- **Action (WHEN)**: Verificar headers dos cards
- **Assert (THEN)**: Cada card contém um label text (chip) visível

#### Scenario: Refinement input visible after AI response
- **Test type**: e2e
- **Test file**: `tests/e2e/test_draft_carousel.py`
- **Test name**: `test_refinement_input_visible`
- **Setup (GIVEN)**: Conversa com Copilot message e drafts
- **Action (WHEN)**: Localizar input de refinamento
- **Assert (THEN)**: Input com placeholder "Refine" visível, ícone `psychology_alt` presente, botão refresh adjacente

#### Scenario: Refinement triggers regeneration
- **Test type**: e2e
- **Test file**: `tests/e2e/test_draft_carousel.py`
- **Test name**: `test_refinement_triggers_regen_request`
- **Setup (GIVEN)**: Conversa com drafts, intercept de rede ativo
- **Action (WHEN)**: Digitar texto no refinement input, click refresh
- **Assert (THEN)**: Request POST para `/regenerate` disparado com `operator_instruction` no body

### Capability: compose-toolbar

#### Scenario: Toolbar visible when conversation open
- **Test type**: e2e
- **Test file**: `tests/e2e/test_compose_toolbar.py`
- **Test name**: `test_compose_toolbar_visible`
- **Setup (GIVEN)**: Conversa aberta
- **Action (WHEN)**: Localizar toolbar no compose area
- **Assert (THEN)**: Botões Formalize (`edit_note`), Translate (`translate`), Attach (`attach_file`) visíveis

#### Scenario: Toolbar layout
- **Test type**: e2e
- **Test file**: `tests/e2e/test_compose_toolbar.py`
- **Test name**: `test_toolbar_layout_order`
- **Setup (GIVEN)**: Toolbar visível
- **Action (WHEN)**: Comparar posições x dos botões
- **Assert (THEN)**: Formalize.x < Translate.x < Attach.x (Attach mais à direita)

#### Scenario: Formalize with text in textarea
- **Test type**: e2e
- **Test file**: `tests/e2e/test_compose_toolbar.py`
- **Test name**: `test_formalize_calls_rewrite`
- **Setup (GIVEN)**: Texto "oi tudo bem" no textarea, intercept ativo para /rewrite
- **Action (WHEN)**: Click Formalize
- **Assert (THEN)**: Request POST para `/rewrite` disparado; textarea atualizado com response

#### Scenario: Formalize with empty textarea
- **Test type**: e2e
- **Test file**: `tests/e2e/test_compose_toolbar.py`
- **Test name**: `test_formalize_noop_empty_textarea`
- **Setup (GIVEN)**: Textarea vazio
- **Action (WHEN)**: Click Formalize
- **Assert (THEN)**: Nenhum request disparado

#### Scenario: Translate with text in textarea
- **Test type**: e2e
- **Test file**: `tests/e2e/test_compose_toolbar.py`
- **Test name**: `test_translate_calls_rewrite`
- **Setup (GIVEN)**: Texto no textarea, intercept ativo
- **Action (WHEN)**: Click Translate
- **Assert (THEN)**: Request POST para `/rewrite` disparado com body contendo instrução de tradução

#### Scenario: Attach opens file dialog
- **Test type**: e2e
- **Test file**: `tests/e2e/test_compose_toolbar.py`
- **Test name**: `test_attach_triggers_file_input`
- **Setup (GIVEN)**: Conversa aberta
- **Action (WHEN)**: Click Attach, set input files via Playwright
- **Assert (THEN)**: `#attachment-bar` visível com nome do arquivo

### Capability: mobile-bottom-nav

#### Scenario: Bottom nav visible on mobile
- **Test type**: e2e
- **Test file**: `tests/e2e/test_bottom_nav.py`
- **Test name**: `test_bottom_nav_visible_mobile`
- **Setup (GIVEN)**: `mobile_page`, conversa aberta
- **Action (WHEN)**: Localizar bottom nav
- **Assert (THEN)**: Nav visível com 3 tabs (Chat, Insights, History)

#### Scenario: Bottom nav hidden on desktop
- **Test type**: e2e
- **Test file**: `tests/e2e/test_bottom_nav.py`
- **Test name**: `test_bottom_nav_hidden_desktop`
- **Setup (GIVEN)**: `desktop_page`, conversa aberta
- **Action (WHEN)**: Localizar bottom nav
- **Assert (THEN)**: Nav não visível (`display: none` ou não renderizado)

#### Scenario: Chat tab is default active
- **Test type**: e2e
- **Test file**: `tests/e2e/test_bottom_nav.py`
- **Test name**: `test_chat_tab_active_by_default`
- **Setup (GIVEN)**: `mobile_page`, conversa aberta
- **Action (WHEN)**: Verificar cor do tab Chat
- **Assert (THEN)**: Tab Chat usa cor primary; Insights e History usam cor muted (30% opacity)

#### Scenario: Tap Insights tab
- **Test type**: e2e
- **Test file**: `tests/e2e/test_bottom_nav.py`
- **Test name**: `test_insights_shows_placeholder`
- **Setup (GIVEN)**: `mobile_page`, conversa aberta
- **Action (WHEN)**: Tap Insights tab
- **Assert (THEN)**: Texto "Em breve" visível na área de conteúdo

#### Scenario: Safe area padding on iPhone
- **Test type**: e2e
- **Test file**: `tests/e2e/test_bottom_nav.py`
- **Test name**: `test_safe_area_padding_css`
- **Setup (GIVEN)**: App carregado
- **Action (WHEN)**: Avaliar CSS do bottom nav
- **Assert (THEN)**: `padding-bottom` inclui `env(safe-area-inset-bottom)` na stylesheet

### Capability: inbox-ui (modified)

#### Scenario: Formalize replaces Reescrever
- **Test type**: e2e
- **Test file**: `tests/e2e/test_inbox_ui.py`
- **Test name**: `test_no_standalone_reescrever_button`
- **Setup (GIVEN)**: Conversa aberta
- **Action (WHEN)**: Buscar botão com texto "Reescrever" no #btn-group
- **Assert (THEN)**: Nenhum botão "Reescrever" encontrado; Formalize disponível na toolbar

#### Scenario: Header with contact info
- **Test type**: e2e
- **Test file**: `tests/e2e/test_inbox_ui.py`
- **Test name**: `test_redesigned_header_elements`
- **Setup (GIVEN)**: Conversa aberta
- **Action (WHEN)**: Inspecionar header
- **Assert (THEN)**: Avatar `img` presente, nome do contato em texto branco, badge de papel visível

#### Scenario: Security banner visible
- **Test type**: e2e
- **Test file**: `tests/e2e/test_inbox_ui.py`
- **Test name**: `test_security_banner`
- **Setup (GIVEN)**: Conversa aberta
- **Action (WHEN)**: Localizar pill de segurança
- **Assert (THEN)**: Texto "Internal Secure Environment" visível com ícone `lock`

#### Scenario: Timestamp styling
- **Test type**: e2e
- **Test file**: `tests/e2e/test_inbox_ui.py`
- **Test name**: `test_timestamp_small_muted`
- **Setup (GIVEN)**: Mensagens visíveis
- **Action (WHEN)**: Avaliar computed style dos timestamps
- **Assert (THEN)**: Font-size <= 11px, color é muted (outline)

### Capability: responsive-layout (modified)

#### Scenario: Carrossel compacto no mobile
- **Test type**: e2e
- **Test file**: `tests/e2e/test_responsive.py`
- **Test name**: `test_mobile_draft_carousel_compact`
- **Setup (GIVEN)**: `mobile_page`, drafts visíveis
- **Action (WHEN)**: Avaliar width dos draft cards
- **Assert (THEN)**: Cards com width ~200px, em carrossel scrollável

#### Scenario: Layout do compose no mobile
- **Test type**: e2e
- **Test file**: `tests/e2e/test_responsive.py`
- **Test name**: `test_mobile_compose_stacked`
- **Setup (GIVEN)**: `mobile_page`, conversa aberta
- **Action (WHEN)**: Verificar layout do compose
- **Assert (THEN)**: Toolbar acima do textarea (toolbar.y < textarea.y)

#### Scenario: Conteúdo não sobreposto pelo bottom nav
- **Test type**: e2e
- **Test file**: `tests/e2e/test_responsive.py`
- **Test name**: `test_content_not_hidden_by_bottom_nav`
- **Setup (GIVEN)**: `mobile_page` com bottom nav visível
- **Action (WHEN)**: Comparar bottom do compose area com top do bottom nav
- **Assert (THEN)**: compose.bottom <= bottomnav.top (sem sobreposição)

### Capability: draft-variations (modified)

#### Scenario: Selection with new visual
- **Test type**: e2e
- **Test file**: `tests/e2e/test_draft_carousel.py`
- **Test name**: `test_draft_selection_primary_bg` (mesmo do carousel)
- **Setup (GIVEN)**: Drafts em carrossel
- **Action (WHEN)**: Click draft B
- **Assert (THEN)**: Card B primary bg, textarea populado

#### Scenario: Refinement replaces instruction bar
- **Test type**: e2e
- **Test file**: `tests/e2e/test_draft_carousel.py`
- **Test name**: `test_no_old_instruction_bar`
- **Setup (GIVEN)**: Conversa com AI message
- **Action (WHEN)**: Buscar `#instruction-bar` no DOM
- **Assert (THEN)**: Elemento antigo não existe ou está hidden; refinement input está no lugar

### Capability: context-panel-ui (modified)

#### Scenario: Panel uses tonal layering
- **Test type**: e2e
- **Test file**: `tests/e2e/test_context_panel.py`
- **Test name**: `test_context_panel_tonal_bg`
- **Setup (GIVEN)**: `desktop_page`, conversa aberta
- **Action (WHEN)**: Avaliar computed background-color do `#context-panel`
- **Assert (THEN)**: Background = surface-container-low (#f3f4f5 ou equivalente rgb)

#### Scenario: Panel uses Veridian styling
- **Test type**: e2e
- **Test file**: `tests/e2e/test_context_panel.py`
- **Test name**: `test_context_panel_inter_font`
- **Setup (GIVEN)**: `desktop_page`, conversa aberta
- **Action (WHEN)**: Avaliar computed font-family do `#context-panel`
- **Assert (THEN)**: Font-family contém "Inter"

### Regressão Backend

#### Scenario: Suite pytest existente passa
- **Test type**: integration
- **Test file**: `tests/` (excluindo `tests/e2e/`)
- **Test name**: `uv run pytest tests/ --ignore=tests/e2e -v`
- **Setup (GIVEN)**: Nenhuma mudança backend
- **Action (WHEN)**: Rodar suite completa
- **Assert (THEN)**: Todos os testes passam

## Coverage Summary

| Capability | Scenario | Test file | Test name | Type |
|------------|----------|-----------|-----------|------|
| e2e-playwright-infra | Dependencies installed | test_infra.py | test_playwright_importable | integration |
| e2e-playwright-infra | Server starts | test_infra.py | test_live_server_responds | integration |
| e2e-playwright-infra | Page loads | test_infra.py | test_page_loads_index | e2e |
| e2e-playwright-infra | Mobile viewport | test_infra.py | test_mobile_viewport_size | e2e |
| e2e-playwright-infra | Seeded conversation | test_infra.py | test_seeded_conversation_in_sidebar | e2e |
| design-tokens-veridian | Primary color | test_design_tokens.py | test_header_uses_primary_color | e2e |
| design-tokens-veridian | Surface tiers | test_design_tokens.py | test_no_1px_borders_between_sections | e2e |
| design-tokens-veridian | Old green removed | test_design_tokens.py | test_no_whatsapp_green_in_css | e2e |
| design-tokens-veridian | Inter font | test_design_tokens.py | test_inter_font_applied | e2e |
| design-tokens-veridian | Material Symbols | test_design_tokens.py | test_material_symbols_present | e2e |
| design-tokens-veridian | Bubble radius | test_design_tokens.py | test_message_bubble_border_radius | e2e |
| design-tokens-veridian | Pill buttons | test_design_tokens.py | test_send_button_pill_shape | e2e |
| design-tokens-veridian | Ghost borders | test_design_tokens.py | test_ghost_borders_only | e2e |
| glass-ai-messages | Bot glassmorphism | test_glass_ai.py | test_bot_message_glass_ai_style | e2e |
| glass-ai-messages | Human outbound | test_glass_ai.py | test_human_outbound_white_bg | e2e |
| glass-ai-messages | Copilot badge | test_glass_ai.py | test_copilot_badge_on_bot_message | e2e |
| glass-ai-messages | No badge human | test_glass_ai.py | test_no_badge_on_human_message | e2e |
| draft-carousel | Three cards | test_draft_carousel.py | test_three_draft_cards_in_carousel | e2e |
| draft-carousel | Peek affordance | test_draft_carousel.py | test_peek_affordance_mobile | e2e |
| draft-carousel | Selection state | test_draft_carousel.py | test_draft_selection_primary_bg | e2e |
| draft-carousel | Card labels | test_draft_carousel.py | test_draft_card_labels | e2e |
| draft-carousel | Refinement input | test_draft_carousel.py | test_refinement_input_visible | e2e |
| draft-carousel | Refinement regen | test_draft_carousel.py | test_refinement_triggers_regen_request | e2e |
| compose-toolbar | Toolbar visible | test_compose_toolbar.py | test_compose_toolbar_visible | e2e |
| compose-toolbar | Toolbar layout | test_compose_toolbar.py | test_toolbar_layout_order | e2e |
| compose-toolbar | Formalize | test_compose_toolbar.py | test_formalize_calls_rewrite | e2e |
| compose-toolbar | Formalize empty | test_compose_toolbar.py | test_formalize_noop_empty_textarea | e2e |
| compose-toolbar | Translate | test_compose_toolbar.py | test_translate_calls_rewrite | e2e |
| compose-toolbar | Attach | test_compose_toolbar.py | test_attach_triggers_file_input | e2e |
| mobile-bottom-nav | Nav visible | test_bottom_nav.py | test_bottom_nav_visible_mobile | e2e |
| mobile-bottom-nav | Nav hidden desktop | test_bottom_nav.py | test_bottom_nav_hidden_desktop | e2e |
| mobile-bottom-nav | Chat active | test_bottom_nav.py | test_chat_tab_active_by_default | e2e |
| mobile-bottom-nav | Insights placeholder | test_bottom_nav.py | test_insights_shows_placeholder | e2e |
| mobile-bottom-nav | Safe area | test_bottom_nav.py | test_safe_area_padding_css | e2e |
| inbox-ui | No Reescrever | test_inbox_ui.py | test_no_standalone_reescrever_button | e2e |
| inbox-ui | Header redesigned | test_inbox_ui.py | test_redesigned_header_elements | e2e |
| inbox-ui | Security banner | test_inbox_ui.py | test_security_banner | e2e |
| inbox-ui | Timestamps | test_inbox_ui.py | test_timestamp_small_muted | e2e |
| responsive-layout | Mobile carousel | test_responsive.py | test_mobile_draft_carousel_compact | e2e |
| responsive-layout | Mobile compose | test_responsive.py | test_mobile_compose_stacked | e2e |
| responsive-layout | No overlap nav | test_responsive.py | test_content_not_hidden_by_bottom_nav | e2e |
| draft-variations | Selection visual | test_draft_carousel.py | test_draft_selection_primary_bg | e2e |
| draft-variations | Refinement replaces bar | test_draft_carousel.py | test_no_old_instruction_bar | e2e |
| context-panel-ui | Tonal layering | test_context_panel.py | test_context_panel_tonal_bg | e2e |
| context-panel-ui | Veridian styling | test_context_panel.py | test_context_panel_inter_font | e2e |
| regressão | Backend suite | tests/ | uv run pytest tests/ --ignore=tests/e2e | integration |
