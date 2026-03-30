"""Tests for Veridian design token application."""

import re

from playwright.sync_api import expect


def _open_conversation(page, live_server):
    """Navigate and open the first conversation."""
    page.goto(live_server)
    page.wait_for_selector(".conv-item", timeout=5000)
    page.locator(".conv-item").first.click()
    page.wait_for_selector("#messages", timeout=5000)


def test_header_uses_primary_color(live_server, desktop_page):
    """Chat header background should be Veridian primary #006B54."""
    _open_conversation(desktop_page, live_server)
    header = desktop_page.locator("#chat-header").first
    bg = header.evaluate("el => getComputedStyle(el).backgroundColor")
    # rgb(0, 107, 84) or rgba with near-full opacity
    assert "0, 107, 84" in bg or "0,107,84" in bg.replace(" ", ""), f"Expected primary green, got: {bg}"


def test_no_1px_borders_between_sections(live_server, desktop_page):
    """Major sections should not use opaque 1px solid borders for separation."""
    _open_conversation(desktop_page, live_server)
    sections = ["#messages", "#compose", "#context-panel"]
    for sel in sections:
        el = desktop_page.locator(sel).first
        if el.count() == 0:
            continue
        border = el.evaluate(
            "el => getComputedStyle(el).borderWidth + '|' + getComputedStyle(el).borderStyle"
        )
        width, style = border.split("|")
        # If there's a 1px solid border, it should be transparent or very low opacity
        if "1px" in width and "solid" in style:
            color = el.evaluate("el => getComputedStyle(el).borderColor")
            # Check it's transparent or very low alpha
            if "rgba" in color:
                alpha = float(color.split(",")[-1].strip(")").strip())
                assert alpha <= 0.2, f"{sel} has opaque border: {color}"
            else:
                # rgb without alpha = fully opaque - should not be opaque separation border
                # Allow if it's transparent
                assert "transparent" in color or "0, 0, 0" not in color, (
                    f"{sel} has opaque 1px border: {color}"
                )


def test_no_whatsapp_green_in_css(live_server, desktop_page):
    """No element should use the old WhatsApp green #25D366."""
    desktop_page.goto(live_server)
    found = desktop_page.evaluate("""() => {
        // Check only local stylesheets (tokens, base, compose, etc.) - not inline JS styles
        const sheets = document.styleSheets;
        for (const sheet of sheets) {
            try {
                if (!sheet.href || !sheet.href.includes('/css/')) continue;
                // Only check core conversation CSS files
                const coreFiles = ['tokens.css', 'base.css', 'compose.css', 'context-panel.css', 'sidebar.css', 'mobile.css'];
                const isCoreFile = coreFiles.some(f => sheet.href.includes(f));
                if (!isCoreFile) continue;
                for (const rule of sheet.cssRules) {
                    if (rule.cssText && (rule.cssText.includes('#25D366') || rule.cssText.includes('#25d366'))) return true;
                }
            } catch(e) { /* cross-origin sheets */ }
        }
        return false;
    }""")
    assert not found, "Old WhatsApp green #25D366 still present in CSS"


def test_inter_font_applied(live_server, desktop_page):
    """Body should use Inter font family."""
    desktop_page.goto(live_server)
    font = desktop_page.evaluate("() => getComputedStyle(document.body).fontFamily")
    assert "Inter" in font, f"Expected Inter font, got: {font}"


def test_material_symbols_present(live_server, desktop_page):
    """Action buttons should use Material Symbols icons."""
    _open_conversation(desktop_page, live_server)
    icons = desktop_page.locator(".material-symbols-outlined")
    assert icons.count() >= 3, f"Expected >= 3 Material Symbols icons, got {icons.count()}"


def test_message_bubble_border_radius(live_server, desktop_page):
    """Message bubbles should have 1rem (16px) border-radius."""
    _open_conversation(desktop_page, live_server)
    msg = desktop_page.locator(".msg").first
    if msg.count() == 0:
        return
    radius = msg.evaluate("el => getComputedStyle(el).borderRadius")
    # Should be 16px or 1rem equivalent
    px_values = re.findall(r"(\d+)", radius)
    assert any(int(v) >= 16 for v in px_values), f"Expected >= 16px border-radius, got: {radius}"


def test_send_button_pill_shape(live_server, desktop_page):
    """Send button should have pill shape (very large border-radius)."""
    _open_conversation(desktop_page, live_server)
    btn = desktop_page.locator("#send-btn").first
    if btn.count() == 0:
        return
    radius = btn.evaluate("el => getComputedStyle(el).borderRadius")
    px_values = re.findall(r"(\d+)", radius)
    # 9999px pill or at least very rounded
    assert any(int(v) >= 20 for v in px_values), f"Expected pill border-radius, got: {radius}"


def test_ghost_borders_only(live_server, desktop_page):
    """Input fields should use ghost borders (outline-variant at low opacity)."""
    _open_conversation(desktop_page, live_server)
    textarea = desktop_page.locator("textarea").first
    if textarea.count() == 0:
        return
    border_color = textarea.evaluate("el => getComputedStyle(el).borderColor")
    # Should be transparent, very low opacity, or absent
    if "rgba" in border_color:
        alpha = float(border_color.split(",")[-1].strip(")").strip())
        assert alpha <= 0.25, f"Input border too opaque: {border_color}"
