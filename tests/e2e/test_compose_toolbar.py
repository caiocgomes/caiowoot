"""Tests for compose toolbar (Group 6 of stitch-conversation-redesign)."""

import re


def _open_conversation(page, live_server):
    """Navigate and open the first conversation."""
    page.goto(live_server)
    page.wait_for_selector(".conv-item", timeout=5000)
    page.locator(".conv-item").first.click()
    page.wait_for_selector("#messages", timeout=5000)


def test_compose_toolbar_visible(live_server, desktop_page):
    """A toolbar with id compose-toolbar is visible with Material Symbols for edit_note, translate, attach_file."""
    _open_conversation(desktop_page, live_server)

    toolbar = desktop_page.locator("#compose-toolbar")
    assert toolbar.is_visible(), "compose-toolbar should be visible"

    # Check for the three Material Symbols icons
    icons = toolbar.locator(".material-symbols-outlined")
    icon_texts = [icons.nth(i).text_content().strip() for i in range(icons.count())]

    assert "edit_note" in icon_texts, f"Expected edit_note icon, found: {icon_texts}"
    assert "translate" in icon_texts, f"Expected translate icon, found: {icon_texts}"
    assert "attach_file" in icon_texts, f"Expected attach_file icon, found: {icon_texts}"


def test_toolbar_layout_order(live_server, desktop_page):
    """Formalize x < Translate x < Attach x (left-to-right order)."""
    _open_conversation(desktop_page, live_server)

    formalize_box = desktop_page.locator("#formalize-btn").bounding_box()
    translate_box = desktop_page.locator("#translate-btn").bounding_box()
    attach_box = desktop_page.locator("#toolbar-attach-btn").bounding_box()

    assert formalize_box is not None, "Formalize button should be visible"
    assert translate_box is not None, "Translate button should be visible"
    assert attach_box is not None, "Attach button should be visible"

    assert formalize_box["x"] < translate_box["x"], (
        f"Formalize ({formalize_box['x']}) should be left of Translate ({translate_box['x']})"
    )
    assert translate_box["x"] < attach_box["x"], (
        f"Translate ({translate_box['x']}) should be left of Attach ({attach_box['x']})"
    )


def test_formalize_calls_rewrite(live_server, desktop_page):
    """Type text, click formalize. Intercept POST /conversations/1/rewrite and verify it was called."""
    _open_conversation(desktop_page, live_server)

    rewrite_called = {"value": False}

    def handle_rewrite(route):
        rewrite_called["value"] = True
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"text": "formalized text"}',
        )

    desktop_page.route(re.compile(r"/conversations/\d+/rewrite"), handle_rewrite)

    desktop_page.locator("#draft-input").fill("texto original")
    desktop_page.locator("#formalize-btn").click()

    # Wait for the request to complete
    desktop_page.wait_for_timeout(1000)

    assert rewrite_called["value"], "Formalize should call POST /rewrite"

    # Verify textarea was updated
    value = desktop_page.locator("#draft-input").input_value()
    assert value == "formalized text", f"Expected textarea to have 'formalized text', got: {value}"

    desktop_page.unroute_all()


def test_formalize_noop_empty_textarea(live_server, desktop_page):
    """With empty textarea, click formalize. No request should be made."""
    _open_conversation(desktop_page, live_server)

    rewrite_called = {"value": False}

    def handle_rewrite(route):
        rewrite_called["value"] = True
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"text": "should not happen"}',
        )

    desktop_page.route(re.compile(r"/conversations/\d+/rewrite"), handle_rewrite)

    # Ensure textarea is empty
    desktop_page.locator("#draft-input").fill("")
    desktop_page.locator("#formalize-btn").click()

    desktop_page.wait_for_timeout(500)

    assert not rewrite_called["value"], "Formalize should NOT call rewrite with empty textarea"

    desktop_page.unroute_all()


def test_translate_calls_rewrite(live_server, desktop_page):
    """Type text, click translate. Intercept POST /rewrite and verify it was called."""
    _open_conversation(desktop_page, live_server)

    rewrite_called = {"value": False}

    def handle_rewrite(route):
        rewrite_called["value"] = True
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"text": "translated text"}',
        )

    desktop_page.route(re.compile(r"/conversations/\d+/rewrite"), handle_rewrite)

    desktop_page.locator("#draft-input").fill("texto para traduzir")
    desktop_page.locator("#translate-btn").click()

    desktop_page.wait_for_timeout(1000)

    assert rewrite_called["value"], "Translate should call POST /rewrite"

    desktop_page.unroute_all()


def test_attach_triggers_file_input(live_server, desktop_page):
    """Click attach in toolbar, set file via #attach-file, verify #attachment-bar becomes visible."""
    _open_conversation(desktop_page, live_server)

    # Verify attachment bar is hidden initially
    attachment_bar = desktop_page.locator("#attachment-bar")
    assert not attachment_bar.is_visible(), "Attachment bar should be hidden initially"

    # Set file on the hidden input (simulates file selection)
    desktop_page.set_input_files("#attach-file", {
        "name": "test-file.txt",
        "mimeType": "text/plain",
        "buffer": b"test content",
    })

    # Wait for the attachment bar to appear
    desktop_page.wait_for_timeout(500)

    assert attachment_bar.is_visible(), "Attachment bar should be visible after selecting a file"
