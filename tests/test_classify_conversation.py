"""Tests for POST /conversations/{id}/classify endpoint."""

from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import *  # noqa: F401, F403


@pytest.mark.asyncio
async def test_classify_conversation_success(client, db):
    """Classify updates funnel_product and funnel_stage when summary returns them."""
    # Setup conversation with messages
    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999999999', 'Maria')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content) VALUES (1, 'inbound', 'Quero saber sobre o curso de LLM')"
    )
    await db.commit()

    mock_summary = AsyncMock(return_value={
        "summary": "Cliente interessada no curso de LLM.",
        "product": "curso-llm",
        "stage": "qualifying",
    })

    with patch("app.routes.conversations.generate_situation_summary", mock_summary):
        resp = await client.post("/conversations/1/classify")

    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"] == "Cliente interessada no curso de LLM."
    assert data["product"] == "curso-llm"
    assert data["stage"] == "qualifying"

    # Verify funnel fields updated in DB
    row = await db.execute("SELECT funnel_product, funnel_stage FROM conversations WHERE id = 1")
    conv = await row.fetchone()
    assert conv["funnel_product"] == "curso-llm"
    assert conv["funnel_stage"] == "qualifying"


@pytest.mark.asyncio
async def test_classify_conversation_no_messages(client, db):
    """Classify with no messages returns nulls."""
    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999999999', 'Maria')"
    )
    await db.commit()

    resp = await client.post("/conversations/1/classify")

    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"] is None
    assert data["product"] is None
    assert data["stage"] is None


@pytest.mark.asyncio
async def test_classify_conversation_not_found(client, db):
    """Classify non-existent conversation returns 404."""
    resp = await client.post("/conversations/99999/classify")
    assert resp.status_code == 404
