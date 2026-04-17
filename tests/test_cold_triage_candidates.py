import pytest

from tests.conftest import *  # noqa: F401, F403

from app.services.cold_triage import select_cold_candidates


async def _seed(
    db,
    phone,
    *,
    stage="link_sent",
    product="curso-cdo",
    last_inbound_offset_days=40,
    cold_do_not_contact=0,
    last_cold_dispatch_offset_days=None,
):
    cursor = await db.execute(
        """INSERT INTO conversations
           (phone_number, contact_name, funnel_product, funnel_stage, cold_do_not_contact)
           VALUES (?, 'X', ?, ?, ?)""",
        (phone, product, stage, cold_do_not_contact),
    )
    conv_id = cursor.lastrowid

    await db.execute(
        f"INSERT INTO messages (conversation_id, direction, content, created_at) "
        f"VALUES (?, 'inbound', 'oi', datetime('now','-{last_inbound_offset_days} days'))",
        (conv_id,),
    )
    if last_cold_dispatch_offset_days is not None:
        await db.execute(
            f"""INSERT INTO cold_dispatches
               (conversation_id, classification, confidence, action, status, created_at)
               VALUES (?, 'objecao_timing', 'high', 'mentoria', 'sent',
                       datetime('now', '-{last_cold_dispatch_offset_days} days'))""",
            (conv_id,),
        )
    await db.commit()
    return conv_id


@pytest.mark.asyncio
async def test_select_filters_product_and_stage(db):
    await _seed(db, "5511", stage="link_sent")
    await _seed(db, "5522", stage="handbook_sent")
    await _seed(db, "5533", stage="qualifying")  # fora do filtro
    await _seed(db, "5544", product="outro")     # produto errado

    rows = await select_cold_candidates(db)
    phones = [r["phone_number"] for r in rows]
    assert "5511" in phones
    assert "5522" in phones
    assert "5533" not in phones
    assert "5544" not in phones


@pytest.mark.asyncio
async def test_select_requires_30_days_cold(db):
    await _seed(db, "5511", last_inbound_offset_days=40)  # elegível
    await _seed(db, "5522", last_inbound_offset_days=10)  # muito fresco

    rows = await select_cold_candidates(db)
    phones = [r["phone_number"] for r in rows]
    assert "5511" in phones
    assert "5522" not in phones


@pytest.mark.asyncio
async def test_select_respects_do_not_contact(db):
    await _seed(db, "5511")
    await _seed(db, "5522", cold_do_not_contact=1)

    rows = await select_cold_candidates(db)
    phones = [r["phone_number"] for r in rows]
    assert "5511" in phones
    assert "5522" not in phones


@pytest.mark.asyncio
async def test_select_respects_cooldown(db):
    await _seed(db, "5511", last_cold_dispatch_offset_days=60)  # dentro do cooldown
    await _seed(db, "5522", last_cold_dispatch_offset_days=100)  # fora
    await _seed(db, "5533", last_cold_dispatch_offset_days=None)  # nunca

    rows = await select_cold_candidates(db)
    phones = [r["phone_number"] for r in rows]
    assert "5511" not in phones
    assert "5522" in phones
    assert "5533" in phones


@pytest.mark.asyncio
async def test_link_sent_comes_before_handbook(db):
    # handbook criado primeiro, link depois — a ordem do select tem que priorizar link
    await _seed(db, "5511", stage="handbook_sent", last_inbound_offset_days=35)
    await _seed(db, "5522", stage="link_sent", last_inbound_offset_days=50)

    rows = await select_cold_candidates(db)
    # link_sent deve aparecer antes
    assert rows[0]["funnel_stage"] == "link_sent"
