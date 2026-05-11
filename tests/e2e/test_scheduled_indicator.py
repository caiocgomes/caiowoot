"""E2E test for the inbox scheduled-send indicator (yellow right border)."""

from datetime import datetime, timedelta

import requests


def _schedule(live_server, conversation_id=1):
    future = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    r = requests.post(
        f"{live_server}/conversations/{conversation_id}/schedule",
        json={"content": "Test scheduled message", "send_at": future},
        timeout=5,
    )
    assert r.status_code == 200, f"schedule POST failed: {r.status_code} {r.text}"
    return r.json()["scheduled_send"]["id"]


def _cancel(live_server, scheduled_id):
    r = requests.delete(f"{live_server}/scheduled-sends/{scheduled_id}", timeout=5)
    assert r.status_code == 200, f"cancel DELETE failed: {r.status_code} {r.text}"


def test_has_scheduled_class_present_when_pending(live_server, desktop_page):
    """Row should get .has-scheduled class when conversation has a pending scheduled send."""
    scheduled_id = _schedule(live_server)
    try:
        desktop_page.goto(live_server)
        desktop_page.wait_for_selector(".conv-item", timeout=5000)
        row = desktop_page.locator(".conv-item").first
        classes = row.get_attribute("class") or ""
        assert "has-scheduled" in classes, f"Expected .has-scheduled, got classes: {classes}"
    finally:
        _cancel(live_server, scheduled_id)


def test_has_scheduled_renders_yellow_right_border(live_server, desktop_page):
    """The row should render a 3px yellow right border via --color-warning token."""
    scheduled_id = _schedule(live_server)
    try:
        desktop_page.goto(live_server)
        desktop_page.wait_for_selector(".conv-item.has-scheduled", timeout=5000)
        row = desktop_page.locator(".conv-item.has-scheduled").first
        width = row.evaluate("el => getComputedStyle(el).borderRightWidth")
        style = row.evaluate("el => getComputedStyle(el).borderRightStyle")
        color = row.evaluate("el => getComputedStyle(el).borderRightColor")
        assert width == "3px", f"Expected border-right 3px, got {width}"
        assert style == "solid", f"Expected solid border, got {style}"
        # --color-warning resolves to a yellow-ish rgb. Just assert it's not the default (transparent/none).
        assert color not in ("rgba(0, 0, 0, 0)", "transparent"), f"Expected colored border, got {color}"
    finally:
        _cancel(live_server, scheduled_id)


def test_no_clock_emoji_in_row(live_server, desktop_page):
    """The old .conv-clock span and clock emoji should be gone from the row."""
    scheduled_id = _schedule(live_server)
    try:
        desktop_page.goto(live_server)
        desktop_page.wait_for_selector(".conv-item.has-scheduled", timeout=5000)
        assert desktop_page.locator(".conv-clock").count() == 0, "Legacy .conv-clock span still present"
        row_text = desktop_page.locator(".conv-item.has-scheduled").first.inner_text()
        assert "\U0001f551" not in row_text, "Clock emoji 🕑 still rendered in row text"
    finally:
        _cancel(live_server, scheduled_id)


def test_class_absent_when_no_scheduled(live_server, desktop_page):
    """Without a pending scheduled send the row should NOT have .has-scheduled."""
    desktop_page.goto(live_server)
    desktop_page.wait_for_selector(".conv-item", timeout=5000)
    row = desktop_page.locator(".conv-item").first
    classes = row.get_attribute("class") or ""
    assert "has-scheduled" not in classes, f"Unexpected .has-scheduled when no pending sends: {classes}"
