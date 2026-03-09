import os
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Override settings BEFORE importing app
os.environ["EVOLUTION_API_URL"] = "http://localhost:8080"
os.environ["EVOLUTION_API_KEY"] = "test-key"
os.environ["EVOLUTION_INSTANCE"] = "test-instance"
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
os.environ["CLAUDE_MODEL"] = "claude-sonnet-4-20250514"
os.environ["CLAUDE_HAIKU_MODEL"] = "claude-haiku-4-5-20251001"
os.environ["DATABASE_PATH"] = ":memory:"
os.environ["APP_PASSWORD"] = ""

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
         patch("app.routes.review.get_db", mock_get_db), \
         patch("app.routes.settings.get_db", mock_get_db), \
         patch("app.services.draft_engine.get_db", mock_get_db), \
         patch("app.services.learned_rules.get_db", mock_get_db), \
         patch("app.services.prompt_config.get_db", mock_get_db), \
         patch("app.services.operator_profile.get_db", mock_get_db), \
         patch("app.services.strategic_annotation.get_db", mock_get_db), \
         patch("app.services.send_executor.get_db", mock_get_db), \
         patch("app.routes.scheduled.get_db", mock_get_db), \
         patch("app.services.scheduler.get_db", mock_get_db), \
         patch("app.services.draft_engine.generate_situation_summary", new_callable=AsyncMock, return_value={"summary": "Primeiro contato genérico.", "product": None, "stage": None}) as mock_summary, \
         patch("app.routes.conversations.generate_situation_summary", new_callable=AsyncMock, return_value={"summary": "Primeiro contato genérico.", "product": None, "stage": None}), \
         patch("app.services.draft_engine.retrieve_similar", return_value=[]) as mock_retrieval, \
         patch("app.services.draft_engine.get_active_rules", new_callable=AsyncMock, return_value=[]) as mock_rules, \
         patch("app.websocket_manager.manager") as mock_ws, \
         patch("app.services.draft_engine.save_prompt", return_value="testhash123"):
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
    """Mock Claude API for draft generation (3 variations) using tool_use."""
    with patch("app.services.draft_engine.anthropic.AsyncAnthropic") as mock:
        mock_client = AsyncMock()

        mock_client.messages.create = AsyncMock(side_effect=[
            make_draft_tool_response("Oi! Qual seu interesse em IA?", "Abordagem direta."),
            make_draft_tool_response("E aí! Me conta, o que te trouxe aqui?", "Abordagem consultiva."),
            make_draft_tool_response("Opa! Tudo bem? Em que posso ajudar?", "Abordagem casual."),
        ])
        mock.return_value = mock_client
        yield mock_client


def make_draft_tool_response(draft="Oi!", justification="Test", suggested_attachment=None):
    """Build a mock Anthropic tool_use response for draft_response."""
    mock_response = MagicMock()
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "draft_response"
    tool_block.input = {"draft": draft, "justification": justification, "suggested_attachment": suggested_attachment}
    mock_response.content = [tool_block]
    return mock_response


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
