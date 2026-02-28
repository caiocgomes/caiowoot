import os
import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Override settings BEFORE importing app
os.environ["EVOLUTION_API_URL"] = "http://localhost:8080"
os.environ["EVOLUTION_API_KEY"] = "test-key"
os.environ["EVOLUTION_INSTANCE"] = "test-instance"
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
os.environ["CLAUDE_MODEL"] = "claude-sonnet-4-20250514"
os.environ["DATABASE_PATH"] = ":memory:"

from app.main import app
from app.database import get_db, init_db
import app.database as db_module


class NonClosingConnection:
    """Wrapper that makes close() a no-op for shared test connections."""

    def __init__(self, conn):
        self._conn = conn

    async def close(self):
        pass  # no-op

    def __getattr__(self, name):
        return getattr(self._conn, name)


@pytest_asyncio.fixture
async def db():
    """In-memory SQLite for tests."""
    import aiosqlite
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.executescript(db_module.SCHEMA)
    await conn.commit()

    wrapper = NonClosingConnection(conn)

    async def mock_get_db():
        return wrapper

    with patch("app.database.get_db", mock_get_db), \
         patch("app.routes.webhook.get_db", mock_get_db), \
         patch("app.routes.conversations.get_db", mock_get_db), \
         patch("app.routes.messages.get_db", mock_get_db), \
         patch("app.services.draft_engine.get_db", mock_get_db), \
         patch("app.websocket_manager.manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()
        yield conn

    await conn.close()


@pytest_asyncio.fixture
async def client(db):
    """Test client with mocked DB and WebSocket."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def mock_evolution_api():
    """Mock Evolution API send endpoint."""
    with patch("app.services.evolution.httpx.AsyncClient") as mock:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": True, "id": "sent-123"},
            "status": "PENDING",
        }
        mock_response.raise_for_status = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_claude_api():
    """Mock Claude API for draft generation."""
    with patch("app.services.draft_engine.anthropic.AsyncAnthropic") as mock:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = [
            AsyncMock(text=json.dumps({
                "draft": "Oi! Tudo bem? Qual seu interesse em IA?",
                "justification": "Primeira mensagem, qualificando o lead."
            }))
        ]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock.return_value = mock_client
        yield mock_client


def make_webhook_payload(
    phone="5511999999999",
    text="Oi, quero saber sobre os cursos",
    message_id="msg-123",
    push_name="Maria",
    event="messages.upsert",
    from_me=False,
):
    return {
        "event": event,
        "instance": {"instanceName": "test-instance"},
        "data": {
            "key": {
                "remoteJid": f"{phone}@s.whatsapp.net",
                "fromMe": from_me,
                "id": message_id,
            },
            "pushName": push_name,
            "messageType": "conversation",
            "message": {"conversation": text},
        },
    }
