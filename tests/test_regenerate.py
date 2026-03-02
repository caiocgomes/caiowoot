import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_draft_tool_response(draft, justification):
    mock_response = MagicMock()
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "draft_response"
    tool_block.input = {"draft": draft, "justification": justification, "suggested_attachment": None}
    mock_response.content = [tool_block]
    return mock_response


@pytest.mark.asyncio
async def test_regenerate_single_draft(db, mock_claude_api):
    """15.4: POST /regenerate com draft_index=1 regenera apenas a variação 1."""
    from app.services.draft_engine import generate_drafts, regenerate_draft

    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 'msg-1', 'inbound', 'Quanto custa?')"
    )
    await db.commit()

    # Generate initial 3 drafts
    await generate_drafts(1, 1)

    # Verify 3 drafts exist
    row = await db.execute("SELECT * FROM drafts WHERE conversation_id = 1 ORDER BY variation_index")
    drafts = await row.fetchall()
    assert len(drafts) == 3
    original_texts = [d["draft_text"] for d in drafts]

    # Reset mock for regeneration call
    mock_claude_api.messages.create = AsyncMock(
        return_value=_make_draft_tool_response("Nova resposta regenerada!", "Regenerada.")
    )

    # Regenerate only variation 1
    await regenerate_draft(1, 1, draft_index=1)

    # Verify variation 1 was updated, others unchanged
    row = await db.execute("SELECT * FROM drafts WHERE conversation_id = 1 AND status = 'pending' ORDER BY variation_index")
    updated_drafts = await row.fetchall()
    assert len(updated_drafts) == 3

    # Variation 0 unchanged
    assert updated_drafts[0]["draft_text"] == original_texts[0]
    # Variation 1 regenerated
    assert updated_drafts[1]["draft_text"] == "Nova resposta regenerada!"
    # Variation 2 unchanged
    assert updated_drafts[2]["draft_text"] == original_texts[2]

    # Only 1 Claude call for the regeneration
    assert mock_claude_api.messages.create.call_count == 1


@pytest.mark.asyncio
async def test_regenerate_all_drafts(db, mock_claude_api):
    """15.5: POST /regenerate com draft_index=null regenera todas as 3."""
    from app.services.draft_engine import generate_drafts, regenerate_draft

    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
        "VALUES (1, 'msg-1', 'inbound', 'Quanto custa?')"
    )
    await db.commit()

    # Generate initial 3 drafts
    await generate_drafts(1, 1)

    row = await db.execute("SELECT * FROM drafts WHERE conversation_id = 1 ORDER BY variation_index")
    original_drafts = await row.fetchall()
    assert len(original_drafts) == 3
    original_group_id = original_drafts[0]["draft_group_id"]

    # Reset mock for regeneration
    mock_claude_api.messages.create = AsyncMock(side_effect=[
        _make_draft_tool_response("Regen direta", "R1"),
        _make_draft_tool_response("Regen consultiva", "R2"),
        _make_draft_tool_response("Regen casual", "R3"),
    ])

    # Regenerate all (draft_index=None)
    await regenerate_draft(1, 1, draft_index=None)

    # Verify 3 new drafts exist
    row = await db.execute("SELECT * FROM drafts WHERE conversation_id = 1 AND status = 'pending' ORDER BY variation_index")
    new_drafts = await row.fetchall()
    assert len(new_drafts) == 3

    # All texts are new
    assert new_drafts[0]["draft_text"] == "Regen direta"
    assert new_drafts[1]["draft_text"] == "Regen consultiva"
    assert new_drafts[2]["draft_text"] == "Regen casual"

    # Same group ID is reused
    assert new_drafts[0]["draft_group_id"] == original_group_id

    # 3 Claude calls for full regeneration
    assert mock_claude_api.messages.create.call_count == 3
