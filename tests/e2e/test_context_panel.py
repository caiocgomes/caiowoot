"""Tests for Context Panel Veridian styling."""


def _open_conversation(page, live_server):
    page.goto(live_server)
    page.wait_for_selector(".conv-item", timeout=5000)
    page.locator(".conv-item").first.click()
    page.wait_for_selector("#messages", timeout=5000)


def test_context_panel_tonal_bg(live_server, desktop_page):
    """#context-panel background should be surface-container-low (#f3f4f5 / rgb(243,244,245))."""
    _open_conversation(desktop_page, live_server)
    panel = desktop_page.locator("#context-panel").first
    bg = panel.evaluate("el => getComputedStyle(el).backgroundColor")
    assert "243, 244, 245" in bg or "243,244,245" in bg.replace(" ", ""), (
        f"Expected surface-container-low rgb(243,244,245), got: {bg}"
    )


def test_context_panel_inter_font(live_server, desktop_page):
    """#context-panel font-family should contain 'Inter'."""
    _open_conversation(desktop_page, live_server)
    panel = desktop_page.locator("#context-panel").first
    font = panel.evaluate("el => getComputedStyle(el).fontFamily")
    assert "Inter" in font, f"Expected Inter font, got: {font}"
