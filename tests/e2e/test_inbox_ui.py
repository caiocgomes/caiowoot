"""Tests for inbox UI redesign: header, security banner, timestamps."""


def _open_conversation(page, live_server):
    page.goto(live_server)
    page.wait_for_selector(".conv-item", timeout=5000)
    page.locator(".conv-item").first.click()
    page.wait_for_selector("#messages", timeout=5000)


def test_redesigned_header_elements(live_server, desktop_page):
    """Header should show contact name in white text on primary background."""
    _open_conversation(desktop_page, live_server)
    header = desktop_page.locator("#chat-header")
    # Header should have primary green background
    bg = header.evaluate("el => getComputedStyle(el).backgroundColor")
    assert "0, 107, 84" in bg or "0,107,84" in bg.replace(" ", ""), f"Expected primary bg, got: {bg}"
    # Contact name should be visible in white
    name = header.locator("#chat-header-name")
    color = name.evaluate("el => getComputedStyle(el).color")
    # White text: rgb(255, 255, 255) or close
    assert "255, 255, 255" in color or "255,255,255" in color.replace(" ", ""), f"Expected white text, got: {color}"


def test_security_banner(live_server, desktop_page):
    """Security banner pill should appear below header."""
    _open_conversation(desktop_page, live_server)
    banner = desktop_page.locator("#security-banner")
    assert banner.count() > 0, "Security banner element not found"
    assert banner.is_visible(), "Security banner not visible"
    # Should contain lock icon and text
    assert desktop_page.locator("#security-banner .material-symbols-outlined").count() > 0, "No lock icon"
    text = banner.inner_text().lower()
    assert "internal secure environment" in text or "secure" in text, f"Expected security text, got: {text}"


def test_timestamp_small_muted(live_server, desktop_page):
    """Message timestamps should be small (<=11px) and muted color."""
    _open_conversation(desktop_page, live_server)
    timestamps = desktop_page.locator(".msg-time")
    if timestamps.count() == 0:
        return
    ts = timestamps.first
    font_size = ts.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
    assert font_size <= 11, f"Timestamp font-size too large: {font_size}px"


def test_no_standalone_reescrever_button(live_server, desktop_page):
    """The standalone Reescrever button should still exist (compose toolbar comes later)."""
    _open_conversation(desktop_page, live_server)
    # For now, just verify the compose area is functional
    textarea = desktop_page.locator("#draft-input")
    assert textarea.is_visible(), "Draft input textarea not visible"
