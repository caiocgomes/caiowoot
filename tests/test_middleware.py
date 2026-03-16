import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db_connection


@pytest.mark.asyncio
async def test_protected_route_returns_401_when_password_set():
    with patch("app.auth.settings") as s:
        s.app_password = "secret123"
        s.session_max_age = 3600
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/conversations")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_bypasses_auth():
    """Webhook should be accessible even when password is set."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.close = AsyncMock()

    async def override_get_db_connection():
        yield mock_db

    app.dependency_overrides[get_db_connection] = override_get_db_connection
    try:
        with patch("app.auth.settings") as s:
            s.app_password = "secret123"
            s.session_max_age = 3600

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/webhook", json={
                    "event": "messages.upsert",
                    "instance": {"instanceName": "test"},
                    "data": {"key": {"remoteJid": "123@s.whatsapp.net", "fromMe": False, "id": "m1"},
                             "pushName": "Test", "messageType": "conversation",
                             "message": {"conversation": "hello"}}
                })
        # Should not be 401 - webhook is in allowlist
        assert resp.status_code != 401
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_endpoint_bypasses_auth():
    with patch("app.auth.settings") as s, \
         patch("app.routes.login.check_password", return_value=False), \
         patch("app.routes.login.check_rate_limit", return_value=True):
        s.app_password = "secret123"
        s.session_max_age = 3600
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/login", json={"password": "wrong"})
    # Should get 401 from login logic, not from middleware redirect
    assert resp.status_code == 401
    assert "Wrong password" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_middleware_disabled_when_no_password():
    """When APP_PASSWORD is empty, all routes should be accessible (not blocked by auth)."""
    mock_db = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.fetchall = AsyncMock(return_value=[])
    mock_db.execute = AsyncMock(return_value=mock_cursor)
    mock_db.close = AsyncMock()

    async def override_get_db_connection():
        yield mock_db

    app.dependency_overrides[get_db_connection] = override_get_db_connection
    try:
        with patch("app.auth.settings") as s:
            s.app_password = ""

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/conversations")
        # Should not be 401 - middleware is disabled
        assert resp.status_code != 401
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_html_request_redirects_to_login():
    with patch("app.auth.settings") as s:
        s.app_password = "secret123"
        s.session_max_age = 3600
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
            resp = await client.get("/", headers={"Accept": "text/html"})
    assert resp.status_code == 302
    assert "/login.html" in resp.headers.get("location", "")
