import os
import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
import aiosqlite
from httpx import AsyncClient, ASGITransport

import app.database as db_module
from app.main import app
from app.auth import create_session_cookie, COOKIE_NAME
from app.config import settings
from app.database import get_db_connection


class NonClosingConnection:
    def __init__(self, conn):
        self._conn = conn
    async def close(self):
        pass
    def __getattr__(self, name):
        return getattr(self._conn, name)


@pytest_asyncio.fixture
async def db():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.executescript(db_module.SCHEMA)
    await conn.commit()

    wrapper = NonClosingConnection(conn)

    async def mock_get_db():
        return wrapper

    async def override_get_db_connection():
        yield wrapper

    app.dependency_overrides[get_db_connection] = override_get_db_connection

    with patch("app.database.get_db", mock_get_db), \
         patch("app.services.draft_engine.get_db", mock_get_db), \
         patch("app.services.learned_rules.get_db", mock_get_db), \
         patch("app.services.prompt_config.get_db", mock_get_db), \
         patch("app.services.operator_profile.get_db", mock_get_db), \
         patch("app.services.draft_engine.generate_situation_summary", new_callable=AsyncMock, return_value="Primeiro contato genérico."), \
         patch("app.services.draft_engine.retrieve_similar", return_value=[]), \
         patch("app.services.draft_engine.get_active_rules", new_callable=AsyncMock, return_value=[]), \
         patch("app.websocket_manager.manager") as mock_ws, \
         patch("app.services.draft_engine.save_prompt", return_value="testhash123"):
        mock_ws.broadcast = AsyncMock()
        yield conn

    app.dependency_overrides.clear()
    await conn.close()


@pytest_asyncio.fixture
async def admin_client(db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        with patch.object(settings, "app_password", "testpass"), \
             patch.object(settings, "operators", "Caio,João"), \
             patch.object(settings, "admin_operator", "Caio"):
            cookie = create_session_cookie(operator="Caio")
            c.cookies.set(COOKIE_NAME, cookie)
            yield c


@pytest_asyncio.fixture
async def non_admin_client(db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        with patch.object(settings, "app_password", "testpass"), \
             patch.object(settings, "operators", "Caio,João"), \
             patch.object(settings, "admin_operator", "Caio"):
            cookie = create_session_cookie(operator="João")
            c.cookies.set(COOKIE_NAME, cookie)
            yield c


# --- GET /api/settings/prompts ---

@pytest.mark.asyncio
async def test_get_prompts_returns_defaults(admin_client):
    resp = await admin_client.get("/api/settings/prompts")
    assert resp.status_code == 200
    data = resp.json()
    assert "postura" in data
    assert "tom" in data
    assert "approach_direta" in data
    assert "summary_prompt" in data
    assert "annotation_prompt" in data


@pytest.mark.asyncio
async def test_get_prompts_accessible_by_non_admin(non_admin_client):
    resp = await non_admin_client.get("/api/settings/prompts")
    assert resp.status_code == 200


# --- PUT /api/settings/prompts ---

@pytest.mark.asyncio
async def test_put_prompts_as_admin(admin_client):
    resp = await admin_client.put(
        "/api/settings/prompts",
        json={"postura": "Nova postura"},
    )
    assert resp.status_code == 200

    resp = await admin_client.get("/api/settings/prompts")
    assert resp.json()["postura"] == "Nova postura"


@pytest.mark.asyncio
async def test_put_prompts_as_non_admin_returns_403(non_admin_client):
    resp = await non_admin_client.put(
        "/api/settings/prompts",
        json={"postura": "Tentativa"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_put_prompts_reset_with_null(admin_client):
    from app.services.prompt_config import PROMPT_DEFAULTS

    await admin_client.put("/api/settings/prompts", json={"postura": "Custom"})
    resp = await admin_client.get("/api/settings/prompts")
    assert resp.json()["postura"] == "Custom"

    await admin_client.put("/api/settings/prompts", json={"postura": None})
    resp = await admin_client.get("/api/settings/prompts")
    assert resp.json()["postura"] == PROMPT_DEFAULTS["postura"]


# --- GET /api/settings/profile ---

@pytest.mark.asyncio
async def test_get_profile_returns_empty_when_none(admin_client):
    resp = await admin_client.get("/api/settings/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] is None or data["display_name"] == ""
    assert data["context"] is None or data["context"] == ""


# --- PUT /api/settings/profile ---

@pytest.mark.asyncio
async def test_put_and_get_profile(admin_client):
    resp = await admin_client.put(
        "/api/settings/profile",
        json={"display_name": "Caio Gomes", "context": "Sou o dono dos cursos"},
    )
    assert resp.status_code == 200

    resp = await admin_client.get("/api/settings/profile")
    data = resp.json()
    assert data["display_name"] == "Caio Gomes"
    assert data["context"] == "Sou o dono dos cursos"


@pytest.mark.asyncio
async def test_profile_isolated_per_operator(admin_client, non_admin_client):
    await admin_client.put(
        "/api/settings/profile",
        json={"display_name": "Caio", "context": "Sou o dono"},
    )
    await non_admin_client.put(
        "/api/settings/profile",
        json={"display_name": "João", "context": "Sou da equipe"},
    )

    resp = await admin_client.get("/api/settings/profile")
    assert resp.json()["context"] == "Sou o dono"

    resp = await non_admin_client.get("/api/settings/profile")
    assert resp.json()["context"] == "Sou da equipe"


# --- GET /api/settings/is-admin ---

@pytest.mark.asyncio
async def test_is_admin_endpoint_for_admin(admin_client):
    resp = await admin_client.get("/api/settings/is-admin")
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is True


@pytest.mark.asyncio
async def test_is_admin_endpoint_for_non_admin(non_admin_client):
    resp = await non_admin_client.get("/api/settings/is-admin")
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is False
