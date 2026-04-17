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
    last_outbound_offset_days=None,
    cold_do_not_contact=0,
    last_cold_dispatch_offset_days=None,
    cold_dispatch_status="sent",
):
    cursor = await db.execute(
        """INSERT INTO conversations
           (phone_number, contact_name, funnel_product, funnel_stage, cold_do_not_contact)
           VALUES (?, 'X', ?, ?, ?)""",
        (phone, product, stage, cold_do_not_contact),
    )
    conv_id = cursor.lastrowid

    if last_inbound_offset_days is not None:
        await db.execute(
            f"INSERT INTO messages (conversation_id, direction, content, created_at) "
            f"VALUES (?, 'inbound', 'oi', datetime('now','-{last_inbound_offset_days} days'))",
            (conv_id,),
        )
    if last_outbound_offset_days is not None:
        await db.execute(
            f"INSERT INTO messages (conversation_id, direction, content, created_at) "
            f"VALUES (?, 'outbound', 'aqui esta o link', datetime('now','-{last_outbound_offset_days} days'))",
            (conv_id,),
        )
    if last_cold_dispatch_offset_days is not None:
        await db.execute(
            f"""INSERT INTO cold_dispatches
               (conversation_id, classification, confidence, action, status, created_at)
               VALUES (?, 'objecao_timing', 'high', 'mentoria', ?,
                       datetime('now', '-{last_cold_dispatch_offset_days} days'))""",
            (conv_id, cold_dispatch_status),
        )
    await db.commit()
    return conv_id


@pytest.mark.asyncio
async def test_select_filters_product_but_not_stage(db):
    """Opção B: stage não filtra. Todos os produtos CDO frios passam, stage é inferido depois."""
    await _seed(db, "5511", stage="link_sent")
    await _seed(db, "5522", stage="handbook_sent")
    await _seed(db, "5533", stage="qualifying")       # agora passa, stage é inferido
    await _seed(db, "5577", stage=None)               # stage NULL também passa
    await _seed(db, "5588", stage="coisa_estranha")   # stage inventado também passa
    await _seed(db, "5544", product="outro")          # produto errado, pula

    rows = await select_cold_candidates(db)
    phones = [r["phone_number"] for r in rows]
    assert "5511" in phones
    assert "5522" in phones
    assert "5533" in phones
    assert "5577" in phones
    assert "5588" in phones
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
async def test_select_respects_cooldown_for_sent_only(db):
    """Cooldown bloqueia leads com dispatch sent/approved. 'previewed' não bloqueia."""
    await _seed(db, "5511", last_cold_dispatch_offset_days=60, cold_dispatch_status="sent")        # bloqueado
    await _seed(db, "5522", last_cold_dispatch_offset_days=100, cold_dispatch_status="sent")       # liberou (>90d)
    await _seed(db, "5533", last_cold_dispatch_offset_days=None)                                    # nunca tocado
    await _seed(db, "5544", last_cold_dispatch_offset_days=60, cold_dispatch_status="previewed")   # NÃO bloqueia, foi só preview
    await _seed(db, "5566", last_cold_dispatch_offset_days=60, cold_dispatch_status="skipped")     # NÃO bloqueia, pulou

    rows = await select_cold_candidates(db)
    phones = [r["phone_number"] for r in rows]
    assert "5511" not in phones
    assert "5522" in phones
    assert "5533" in phones
    assert "5544" in phones
    assert "5566" in phones


@pytest.mark.asyncio
async def test_select_includes_outbound_last_leads(db):
    """Leads onde operador foi o último a falar (outbound) e lead silenciou também entram."""
    # Lead 1: última inbound há 60d, operador mandou link há 40d e lead nunca respondeu.
    await _seed(db, "5511", last_inbound_offset_days=60, last_outbound_offset_days=40)
    # Lead 2: última inbound há 15d (recente). Operador ainda espera resposta, não é cold.
    await _seed(db, "5522", last_inbound_offset_days=15, last_outbound_offset_days=14)
    # Lead 3: última inbound há 40d, operador acabou de tentar follow-up ontem (1d).
    # Atividade recente, NÃO é cold ainda.
    await _seed(db, "5533", last_inbound_offset_days=40, last_outbound_offset_days=1)
    # Lead 4: só outbound (conversa onde lead não respondeu nunca). 50d.
    await _seed(db, "5544", last_inbound_offset_days=None, last_outbound_offset_days=50)

    rows = await select_cold_candidates(db)
    phones = [r["phone_number"] for r in rows]
    assert "5511" in phones
    assert "5522" not in phones
    assert "5533" not in phones  # follow-up recente do operador tira do pool
    assert "5544" in phones


@pytest.mark.asyncio
async def test_candidates_ordered_by_freshness(db):
    """Sem filtro de stage, o SELECT só ordena por frescor. A priorização por stage_reached
    acontece depois da classificação, no score_candidate."""
    await _seed(db, "5511", stage="link_sent", last_inbound_offset_days=55)
    await _seed(db, "5522", stage="handbook_sent", last_inbound_offset_days=35)

    rows = await select_cold_candidates(db)
    # Mais fresco (35 dias) vem antes
    assert rows[0]["phone_number"] == "5522"
