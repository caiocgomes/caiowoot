"""Tests for draft carousel (Group 5 of stitch-conversation-redesign)."""


def _open_conversation(page, live_server):
    """Navigate and open the first conversation, wait for drafts."""
    page.goto(live_server)
    page.wait_for_selector(".conv-item", timeout=5000)
    page.locator(".conv-item").first.click()
    page.wait_for_selector("#messages", timeout=5000)
    # Wait for drafts to appear
    page.wait_for_selector(".draft-card", timeout=5000)


def test_three_draft_cards_in_carousel(live_server, desktop_page):
    """Three .draft-card elements visible; container has overflow-x: auto and scroll-snap-type containing 'x'."""
    _open_conversation(desktop_page, live_server)

    cards = desktop_page.locator(".draft-card")
    assert cards.count() == 3, f"Expected 3 draft cards, got {cards.count()}"

    draft_cards_el = desktop_page.locator("#draft-cards")
    overflow_x = draft_cards_el.evaluate("el => getComputedStyle(el).overflowX")
    assert overflow_x == "auto", f"Expected overflow-x: auto, got: {overflow_x}"

    snap_type = draft_cards_el.evaluate("el => getComputedStyle(el).scrollSnapType")
    assert "x" in snap_type, f"Expected scroll-snap-type containing 'x', got: {snap_type}"


def test_peek_affordance_mobile(live_server, mobile_page):
    """On 390px viewport, draft container scrollWidth > clientWidth (peek affordance)."""
    _open_conversation(mobile_page, live_server)

    result = mobile_page.locator("#draft-cards").evaluate(
        "el => ({ scrollWidth: el.scrollWidth, clientWidth: el.clientWidth })"
    )
    assert result["scrollWidth"] > result["clientWidth"], (
        f"Expected scrollWidth ({result['scrollWidth']}) > clientWidth ({result['clientWidth']}) for peek affordance"
    )


def test_draft_selection_primary_bg(live_server, desktop_page):
    """Click second card: it gets primary bg (#006B54 / rgb(0,107,84)), others have white bg."""
    _open_conversation(desktop_page, live_server)

    cards = desktop_page.locator(".draft-card")
    # Click the second card
    cards.nth(1).click()

    # Wait for the selected class to be applied
    desktop_page.locator(".draft-card.selected").wait_for(timeout=3000)

    # Wait for CSS transition to complete (transition: all 0.2s ease)
    desktop_page.wait_for_timeout(300)

    # Second card should have primary background
    bg_selected = cards.nth(1).evaluate("el => getComputedStyle(el).backgroundColor")
    assert "0, 107, 84" in bg_selected or "0,107,84" in bg_selected.replace(" ", ""), (
        f"Expected primary green bg on selected card, got: {bg_selected}"
    )

    # First and third should have white/light bg (not primary)
    for idx in [0, 2]:
        bg = cards.nth(idx).evaluate("el => getComputedStyle(el).backgroundColor")
        assert "0, 107, 84" not in bg and "0,107,84" not in bg.replace(" ", ""), (
            f"Card {idx} should not have primary bg, got: {bg}"
        )


def test_draft_card_labels(live_server, desktop_page):
    """Each card has a .draft-card-label element with visible text."""
    _open_conversation(desktop_page, live_server)

    labels = desktop_page.locator(".draft-card-label")
    assert labels.count() == 3, f"Expected 3 labels, got {labels.count()}"

    for i in range(3):
        text = labels.nth(i).text_content().strip()
        assert len(text) > 0, f"Label {i} has no text"
        assert labels.nth(i).is_visible(), f"Label {i} is not visible"


def test_refinement_input_visible(live_server, desktop_page):
    """An input with placeholder containing 'Instrução' is visible with a refresh button."""
    _open_conversation(desktop_page, live_server)

    instruction_input = desktop_page.locator("#instruction-input")
    assert instruction_input.is_visible(), "Instruction input should be visible"

    placeholder = instruction_input.get_attribute("placeholder") or ""
    assert "Instrução" in placeholder or "Refine" in placeholder, (
        f"Expected placeholder containing 'Instrução' or 'Refine', got: {placeholder}"
    )

    # Refresh/regenerate button should exist near the input
    regen_btn = desktop_page.locator("#regen-instruction-btn")
    assert regen_btn.is_visible(), "Regenerate instruction button should be visible"


def test_refinement_triggers_regen_request(live_server, desktop_page):
    """Type in refinement input, click refresh, intercept network to verify POST to /regenerate with operator_instruction."""
    _open_conversation(desktop_page, live_server)

    # Type instruction
    instruction_input = desktop_page.locator("#instruction-input")
    instruction_input.fill("foca no preço")

    # Intercept the regenerate request
    with desktop_page.expect_request(
        lambda req: "/regenerate" in req.url and req.method == "POST",
        timeout=5000,
    ) as request_info:
        desktop_page.locator("#regen-instruction-btn").click()

    request = request_info.value
    body = request.post_data_json
    assert body is not None, "Expected JSON body in regenerate request"
    assert body.get("operator_instruction") == "foca no preço", (
        f"Expected operator_instruction='foca no preço', got: {body.get('operator_instruction')}"
    )


def test_no_old_instruction_bar(live_server, desktop_page):
    """The #instruction-bar element should still exist (it is the refinement input) with proper styling."""
    _open_conversation(desktop_page, live_server)

    instruction_bar = desktop_page.locator("#instruction-bar")
    assert instruction_bar.count() == 1, "instruction-bar should still exist in DOM"

    # Verify it has the new styling (instruction-row layout)
    instruction_row = desktop_page.locator("#instruction-bar .instruction-row")
    assert instruction_row.count() == 1, "instruction-bar should contain .instruction-row"

    display = instruction_row.evaluate("el => getComputedStyle(el).display")
    assert display == "flex", f"Expected flex layout for instruction-row, got: {display}"
