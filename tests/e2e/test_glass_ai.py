"""Tests for glass AI message styling and Copilot badge."""

from playwright.sync_api import expect


def _open_conversation(page, live_server):
    """Navigate and open the first conversation."""
    page.goto(live_server)
    page.wait_for_selector(".conv-item", timeout=5000)
    page.locator(".conv-item").first.click()
    page.wait_for_selector("#messages", timeout=5000)


def test_bot_message_glass_ai_style(live_server, desktop_page):
    """Bot messages should have glass-ai class, background rgba(0,107,84,0.04), backdrop-filter blur."""
    _open_conversation(desktop_page, live_server)
    bot_msg = desktop_page.locator(".msg.outbound.bot").first
    expect(bot_msg).to_be_visible()

    # Check glass-ai background
    bg = bot_msg.evaluate("el => getComputedStyle(el).backgroundColor")
    assert "0, 107, 84" in bg or "0,107,84" in bg.replace(" ", ""), (
        f"Expected glass-ai green-tinted background, got: {bg}"
    )

    # Check backdrop-filter blur
    backdrop = bot_msg.evaluate(
        "el => getComputedStyle(el).backdropFilter || getComputedStyle(el).webkitBackdropFilter || ''"
    )
    assert "blur" in backdrop, f"Expected backdrop-filter blur, got: {backdrop}"


def test_human_outbound_white_bg(live_server, desktop_page):
    """Human outbound messages should have white background, no glass-ai class."""
    _open_conversation(desktop_page, live_server)
    # Human outbound = outbound without .bot class
    human_msgs = desktop_page.locator(".msg.outbound:not(.bot)")
    expect(human_msgs.first).to_be_visible()

    # Should not have glass-ai class
    has_glass = human_msgs.first.evaluate("el => el.classList.contains('glass-ai')")
    assert not has_glass, "Human outbound should not have glass-ai class"

    # Should have white-ish background (surface-container-lowest = #ffffff)
    bg = human_msgs.first.evaluate("el => getComputedStyle(el).backgroundColor")
    assert "255, 255, 255" in bg or "255,255,255" in bg.replace(" ", ""), (
        f"Expected white background for human outbound, got: {bg}"
    )


def test_copilot_badge_on_bot_message(live_server, desktop_page):
    """Bot messages should show 'Veridian Copilot' badge with auto_awesome icon above the bubble."""
    _open_conversation(desktop_page, live_server)
    bot_msg = desktop_page.locator(".msg.outbound.bot").first
    expect(bot_msg).to_be_visible()

    # Badge should exist before the bot message (as a previous sibling in #messages)
    # We look for the badge inside the wrapper that contains the bot message
    badge = desktop_page.locator(".copilot-badge")
    expect(badge.first).to_be_visible()

    # Badge should contain the icon
    icon = badge.first.locator(".copilot-badge-icon .material-symbols-outlined")
    expect(icon).to_be_visible()
    assert icon.text_content().strip() == "auto_awesome"

    # Badge should contain "Veridian Copilot" text
    text = badge.first.locator(".copilot-badge-text")
    expect(text).to_be_visible()
    assert "Veridian Copilot" in text.text_content()


def test_no_badge_on_human_message(live_server, desktop_page):
    """Human outbound messages should NOT show Copilot badge."""
    _open_conversation(desktop_page, live_server)

    # Count badges vs bot messages - should be equal
    badges = desktop_page.locator(".copilot-badge")
    bot_msgs = desktop_page.locator(".msg.outbound.bot")

    badge_count = badges.count()
    bot_count = bot_msgs.count()

    assert badge_count == bot_count, (
        f"Badge count ({badge_count}) should equal bot message count ({bot_count})"
    )

    # Verify no badge is adjacent to a human outbound message
    # Each badge's next sibling should be a .msg.outbound.bot
    for i in range(badge_count):
        next_is_bot = badges.nth(i).evaluate(
            "el => el.nextElementSibling && el.nextElementSibling.classList.contains('bot')"
        )
        assert next_is_bot, f"Badge {i} is not followed by a bot message"
