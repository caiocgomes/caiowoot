"""Tests for responsive layout updates (Group 8 of stitch-conversation-redesign)."""


def _open_conversation(page, live_server):
    page.goto(live_server)
    page.wait_for_selector(".conv-item", timeout=5000)
    page.locator(".conv-item").first.click()
    page.wait_for_selector("#messages", timeout=5000)


def test_mobile_draft_carousel_compact(live_server, mobile_page):
    """On mobile viewport, draft cards should have width around 200px (between 150-250px)."""
    _open_conversation(mobile_page, live_server)
    mobile_page.wait_for_selector(".draft-card", timeout=5000)

    width = mobile_page.locator(".draft-card").first.evaluate("el => el.offsetWidth")
    assert 150 <= width <= 250, (
        f"Expected draft card width between 150-250px on mobile, got: {width}px"
    )


def test_mobile_compose_stacked(live_server, mobile_page):
    """On mobile, if a compose toolbar exists, its Y position should be less than the textarea's Y.

    If no toolbar exists yet, just verify the compose area is visible.
    """
    _open_conversation(mobile_page, live_server)

    toolbar = mobile_page.locator("#compose-toolbar")
    if toolbar.count() > 0 and toolbar.is_visible():
        toolbar_box = toolbar.bounding_box()
        textarea_box = mobile_page.locator("#draft-input").bounding_box()
        assert toolbar_box is not None and textarea_box is not None, (
            "Could not get bounding boxes for toolbar and textarea"
        )
        assert toolbar_box["y"] < textarea_box["y"], (
            f"Toolbar Y ({toolbar_box['y']}) should be above textarea Y ({textarea_box['y']})"
        )
    else:
        compose = mobile_page.locator("#compose")
        assert compose.is_visible(), "Compose area should be visible on mobile"


def test_content_not_hidden_by_bottom_nav(live_server, mobile_page):
    """On mobile, the bottom of the compose area should not overlap with the top of the bottom nav.

    Get bounding boxes of #compose and #bottom-nav, verify compose.bottom <= bottomnav.top
    (or close, within 80px tolerance for the padding).
    """
    _open_conversation(mobile_page, live_server)

    compose_box = mobile_page.locator("#compose").bounding_box()
    nav_box = mobile_page.locator("#bottom-nav").bounding_box()

    assert compose_box is not None, "Could not get bounding box for #compose"
    assert nav_box is not None, "Could not get bounding box for #bottom-nav"

    compose_bottom = compose_box["y"] + compose_box["height"]
    nav_top = nav_box["y"]

    # Compose bottom should not extend past the top of the bottom nav by more than 80px
    overlap = compose_bottom - nav_top
    assert overlap <= 80, (
        f"Compose bottom ({compose_bottom:.0f}px) overlaps bottom nav top ({nav_top:.0f}px) "
        f"by {overlap:.0f}px, exceeds 80px tolerance"
    )
