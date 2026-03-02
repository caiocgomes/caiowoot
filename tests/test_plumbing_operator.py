"""Tests for operator_name plumbing through regenerate and suggest endpoints."""
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.auth import create_session_cookie, COOKIE_NAME
from app.config import settings


@pytest.mark.asyncio
async def test_regenerate_passes_operator_name(client, db, mock_claude_api):
    """regenerate endpoint should pass operator_name from cookie to regenerate_draft."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.commit()

    # Generate initial drafts
    from app.services.draft_engine import generate_drafts
    await generate_drafts(1, 1)

    with patch("app.routes.messages.regenerate_draft", new_callable=AsyncMock) as mock_regen, \
         patch.object(settings, "app_password", "testpass"), \
         patch.object(settings, "operators", "João,Caio"):
        cookie = create_session_cookie(operator="João")
        client.cookies.set(COOKIE_NAME, cookie)

        resp = await client.post(
            "/conversations/1/regenerate",
            json={"trigger_message_id": 1, "draft_index": 0},
        )
        assert resp.status_code == 200

        mock_regen.assert_called_once()
        call_kwargs = mock_regen.call_args
        assert call_kwargs.kwargs.get("operator_name") == "João" or \
               (len(call_kwargs.args) > 4 and call_kwargs.args[4] == "João")


@pytest.mark.asyncio
async def test_suggest_passes_operator_name(client, db, mock_claude_api):
    """suggest endpoint should pass operator_name from cookie to generate_drafts."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 'msg-1', 'inbound', 'Oi')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content) "
        "VALUES (1, 'outbound', 'Falo contigo!')"
    )
    await db.commit()

    with patch("app.services.draft_engine.generate_drafts", new_callable=AsyncMock) as mock_gen, \
         patch.object(settings, "app_password", "testpass"), \
         patch.object(settings, "operators", "João,Caio"):
        cookie = create_session_cookie(operator="João")
        client.cookies.set(COOKIE_NAME, cookie)

        resp = await client.post("/conversations/1/suggest")
        assert resp.status_code == 200

        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args
        assert call_kwargs.kwargs.get("operator_name") == "João"
