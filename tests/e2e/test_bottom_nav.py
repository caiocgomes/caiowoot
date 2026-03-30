"""Tests for mobile bottom navigation."""

import re


def _open_conversation(page, live_server):
    page.goto(live_server)
    page.wait_for_selector(".conv-item", timeout=5000)
    page.locator(".conv-item").first.click()
    page.wait_for_selector("#messages", timeout=5000)


def test_bottom_nav_visible_mobile(live_server, mobile_page):
    """Bottom nav visible on mobile after opening conversation. Should contain Chat, Insights, History."""
    _open_conversation(mobile_page, live_server)
    nav = mobile_page.locator("#bottom-nav")
    assert nav.is_visible(), "Bottom nav should be visible on mobile"
    text = nav.inner_text().lower()
    assert "chat" in text, f"Expected 'Chat' in bottom nav, got: {text}"
    assert "insights" in text, f"Expected 'Insights' in bottom nav, got: {text}"
    assert "history" in text, f"Expected 'History' in bottom nav, got: {text}"


def test_bottom_nav_hidden_desktop(live_server, desktop_page):
    """Bottom nav should NOT be visible on desktop."""
    _open_conversation(desktop_page, live_server)
    nav = desktop_page.locator("#bottom-nav")
    assert not nav.is_visible(), "Bottom nav should be hidden on desktop"


def test_chat_tab_active_by_default(live_server, mobile_page):
    """Chat tab should use primary color, others should be muted."""
    _open_conversation(mobile_page, live_server)
    chat_tab = mobile_page.locator('.bottom-nav-tab[data-tab="chat"]')
    insights_tab = mobile_page.locator('.bottom-nav-tab[data-tab="insights"]')

    chat_color = chat_tab.evaluate("el => getComputedStyle(el).color")
    insights_color = insights_tab.evaluate("el => getComputedStyle(el).color")

    # Chat tab should be primary green (0, 107, 84)
    assert "0, 107, 84" in chat_color or "0,107,84" in chat_color.replace(" ", ""), (
        f"Expected primary color on chat tab, got: {chat_color}"
    )
    # Insights tab should NOT be primary
    assert "0, 107, 84" not in insights_color and "0,107,84" not in insights_color.replace(" ", ""), (
        f"Insights tab should be muted, got: {insights_color}"
    )


def test_insights_shows_placeholder(live_server, mobile_page):
    """Tapping Insights tab shows 'Em breve' placeholder text."""
    _open_conversation(mobile_page, live_server)
    mobile_page.locator('.bottom-nav-tab[data-tab="insights"]').click()
    placeholder = mobile_page.locator("#bottom-nav-placeholder")
    assert placeholder.is_visible(), "Placeholder should be visible after tapping Insights"
    text = placeholder.inner_text()
    assert "Em breve" in text, f"Expected 'Em breve' in placeholder, got: {text}"


def test_safe_area_padding_css(live_server, mobile_page):
    """Verify the bottom nav CSS includes env(safe-area-inset-bottom) in the stylesheet."""
    mobile_page.goto(live_server)
    found = mobile_page.evaluate("""() => {
        const sheets = document.styleSheets;
        for (const sheet of sheets) {
            try {
                if (!sheet.href || !sheet.href.includes('/css/')) continue;
                for (const rule of sheet.cssRules) {
                    if (rule.cssText && rule.cssText.includes('safe-area-inset-bottom')) return true;
                }
            } catch(e) { /* cross-origin sheets */ }
        }
        return false;
    }""")
    assert found, "CSS should include env(safe-area-inset-bottom) for bottom nav"
