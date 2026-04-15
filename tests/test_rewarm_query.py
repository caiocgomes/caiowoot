import pytest

from tests.conftest import *  # noqa: F401, F403

from app.services.rewarm_engine import select_rewarm_candidates


async def _seed_conversation(
    db,
    phone="5511999999999",
    contact_name="Joao",
    funnel_product="curso-cdo",
    funnel_stage="handbook_sent",
    messages_days_ago=None,
    pending_draft=False,
):
    """Helper: creates a conversation with optional messages (list of day offsets) and optional pending draft."""
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) VALUES (?, ?, ?, ?)",
        (phone, contact_name, funnel_product, funnel_stage),
    )
    conv_id = cursor.lastrowid

    if messages_days_ago is None:
        messages_days_ago = [1]  # default: one message from D-1

    for offset in messages_days_ago:
        await db.execute(
            f"INSERT INTO messages (conversation_id, direction, content, created_at) "
            f"VALUES (?, 'inbound', 'teste', datetime('now', '-{offset} day'))",
            (conv_id,),
        )

    if pending_draft:
        # Need a trigger message for draft FK
        trigger_cursor = await db.execute(
            "INSERT INTO messages (conversation_id, direction, content) VALUES (?, 'inbound', 'trigger')",
            (conv_id,),
        )
        trigger_id = trigger_cursor.lastrowid
        await db.execute(
            "INSERT INTO drafts (conversation_id, trigger_message_id, draft_text, status) VALUES (?, ?, 'pending draft', 'pending')",
            (conv_id, trigger_id),
        )

    await db.commit()
    return conv_id


@pytest.mark.asyncio
async def test_query_includes_eligible_conversation(db):
    conv_id = await _seed_conversation(db)
    results = await select_rewarm_candidates(db)
    assert any(r["id"] == conv_id for r in results)


@pytest.mark.asyncio
async def test_query_excludes_other_product(db):
    await _seed_conversation(db, funnel_product="outro-curso")
    results = await select_rewarm_candidates(db)
    assert results == []


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["qualifying", "decided", "purchased"])
async def test_query_excludes_other_stage(db, stage):
    await _seed_conversation(db, phone=f"55999{stage}", funnel_stage=stage)
    results = await select_rewarm_candidates(db)
    assert results == []


@pytest.mark.asyncio
async def test_query_excludes_conversation_without_yesterday_message(db):
    await _seed_conversation(db, messages_days_ago=[3])
    results = await select_rewarm_candidates(db)
    assert results == []


@pytest.mark.asyncio
async def test_query_excludes_conversation_with_pending_draft(db):
    await _seed_conversation(db, pending_draft=True)
    results = await select_rewarm_candidates(db)
    assert results == []


@pytest.mark.asyncio
async def test_query_excludes_purchased(db):
    await _seed_conversation(db, funnel_stage="purchased")
    results = await select_rewarm_candidates(db)
    assert results == []


@pytest.mark.asyncio
async def test_query_includes_link_sent_stage(db):
    conv_id = await _seed_conversation(db, funnel_stage="link_sent")
    results = await select_rewarm_candidates(db)
    assert any(r["id"] == conv_id for r in results)


@pytest.mark.asyncio
async def test_query_returns_contact_fields(db):
    conv_id = await _seed_conversation(db, phone="5511987654321", contact_name="Maria")
    results = await select_rewarm_candidates(db)
    match = next(r for r in results if r["id"] == conv_id)
    assert match["phone_number"] == "5511987654321"
    assert match["contact_name"] == "Maria"
    assert match["funnel_stage"] == "handbook_sent"


@pytest.mark.asyncio
async def test_query_treats_sent_draft_as_not_pending(db):
    """A draft with sent_at NOT NULL should not block the conversation."""
    conv_id = await _seed_conversation(db)
    # Add a sent draft
    trigger_cursor = await db.execute(
        "INSERT INTO messages (conversation_id, direction, content) VALUES (?, 'inbound', 'trigger')",
        (conv_id,),
    )
    # drafts table doesn't have sent_at column - status='sent' is the signal.
    # Check implementation decision: we filter by status != 'pending' OR by sent_at.
    # For now, the test documents the expectation: a 'sent' status draft should not block.
    await db.execute(
        "INSERT INTO drafts (conversation_id, trigger_message_id, draft_text, status) VALUES (?, ?, 'old', 'sent')",
        (conv_id, trigger_cursor.lastrowid),
    )
    await db.commit()
    results = await select_rewarm_candidates(db)
    assert any(r["id"] == conv_id for r in results)
