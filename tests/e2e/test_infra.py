"""Smoke tests for Playwright e2e infrastructure."""

import pytest


def test_playwright_importable():
    """Verify playwright is installed and importable."""
    import playwright
    assert playwright is not None


def test_live_server_responds(live_server):
    """Verify the live server is up and responding."""
    import requests
    r = requests.get(f"{live_server}/health", timeout=5)
    assert r.status_code == 200


def test_page_loads_index(live_server, page):
    """Verify Playwright can navigate to the app."""
    page.goto(live_server)
    # The app should load the index.html with sidebar
    assert page.locator("#sidebar").count() > 0 or page.title() != ""


def test_mobile_viewport_size(live_server, mobile_page):
    """Verify mobile viewport fixture sets correct dimensions."""
    size = mobile_page.viewport_size
    assert size["width"] == 390
    assert size["height"] == 844


def test_seeded_conversation_in_sidebar(live_server, page):
    """Verify seeded conversation appears in the sidebar."""
    page.goto(live_server)
    # Wait for conversation list to load
    page.wait_for_selector(".conv-item", timeout=5000)
    items = page.locator(".conv-item")
    assert items.count() >= 1
    # Check the seeded contact name is visible
    assert page.locator("text=Mabel Coelho").count() >= 1
