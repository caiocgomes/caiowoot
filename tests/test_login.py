import pytest
from unittest.mock import patch

from app.auth import COOKIE_NAME, reset_rate_limit


@pytest.fixture(autouse=True)
def _reset_rate():
    reset_rate_limit()
    yield
    reset_rate_limit()


@pytest.mark.asyncio
async def test_login_correct_password(client, db):
    with patch("app.routes.login.settings") as s, \
         patch("app.routes.login.check_password", return_value=True), \
         patch("app.routes.login.create_session_cookie", return_value="valid-cookie"):
        s.session_max_age = 3600
        resp = await client.post("/login", json={"password": "secret"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert COOKIE_NAME in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client, db):
    with patch("app.routes.login.check_password", return_value=False):
        resp = await client.post("/login", json={"password": "wrong"})
    assert resp.status_code == 401
    assert "Wrong password" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_rate_limited(client, db):
    with patch("app.routes.login.check_rate_limit", return_value=False):
        resp = await client.post("/login", json={"password": "any"})
    assert resp.status_code == 429
    assert "Too many" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_logout_clears_cookie(client, db):
    resp = await client.post("/logout")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    # Cookie should be cleared (set to empty/expired)
    assert COOKIE_NAME in resp.headers.get("set-cookie", "")
