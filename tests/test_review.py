import pytest
from unittest.mock import patch


async def _create_edit_pair(db, annotation=None, was_edited=True):
    await db.execute(
        "INSERT OR IGNORE INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    cursor = await db.execute(
        """INSERT INTO edit_pairs
           (conversation_id, customer_message, original_draft, final_message, was_edited,
            situation_summary, strategic_annotation)
           VALUES (1, 'Quanto custa?', 'O CDO é R$2997', 'Me conta o que vc faz', ?, 'Primeiro contato', ?)""",
        (was_edited, annotation),
    )
    await db.commit()
    return cursor.lastrowid


@pytest.mark.asyncio
async def test_list_pending_annotations(client, db):
    await _create_edit_pair(db, annotation="IA jogou preço sem qualificar.", was_edited=True)
    await _create_edit_pair(db, annotation="Abordagem validada.", was_edited=False)

    resp = await client.get("/review")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stats"]["total_pending"] == 2
    assert data["stats"]["total_edited"] == 1
    assert data["stats"]["total_confirmed"] == 1
    assert len(data["annotations"]) == 2


@pytest.mark.asyncio
async def test_list_excludes_validated(client, db):
    ep_id = await _create_edit_pair(db, annotation="Anotação validada.")
    await db.execute("UPDATE edit_pairs SET validated = 1 WHERE id = ?", (ep_id,))
    await db.commit()

    resp = await client.get("/review")
    assert resp.json()["stats"]["total_pending"] == 0


@pytest.mark.asyncio
async def test_list_excludes_no_annotation(client, db):
    await _create_edit_pair(db, annotation=None)

    resp = await client.get("/review")
    assert resp.json()["stats"]["total_pending"] == 0


@pytest.mark.asyncio
async def test_validate_annotation(client, db):
    ep_id = await _create_edit_pair(db, annotation="Teste.")

    with patch("app.routes.review.update_metadata"):
        resp = await client.post(f"/review/{ep_id}/validate")
    assert resp.status_code == 200
    assert resp.json()["action"] == "validated"

    row = await db.execute("SELECT validated, rejected FROM edit_pairs WHERE id = ?", (ep_id,))
    pair = await row.fetchone()
    assert pair["validated"] == 1
    assert pair["rejected"] == 0


@pytest.mark.asyncio
async def test_reject_annotation(client, db):
    ep_id = await _create_edit_pair(db, annotation="Teste.")

    with patch("app.routes.review.update_metadata"):
        resp = await client.post(f"/review/{ep_id}/reject")
    assert resp.status_code == 200
    assert resp.json()["action"] == "rejected"

    row = await db.execute("SELECT validated, rejected FROM edit_pairs WHERE id = ?", (ep_id,))
    pair = await row.fetchone()
    assert pair["validated"] == 1
    assert pair["rejected"] == 1


@pytest.mark.asyncio
async def test_promote_annotation_to_rule(client, db):
    ep_id = await _create_edit_pair(db, annotation="Sempre qualificar antes de precificar.")

    with patch("app.routes.review.update_metadata"):
        resp = await client.post(f"/review/{ep_id}/promote")
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "promoted"
    assert data["rule"]["rule_text"] == "Sempre qualificar antes de precificar."
    assert data["rule"]["source_edit_pair_id"] == ep_id


@pytest.mark.asyncio
async def test_promote_with_custom_text(client, db):
    ep_id = await _create_edit_pair(db, annotation="Anotação original.")

    with patch("app.routes.review.update_metadata"):
        resp = await client.post(
            f"/review/{ep_id}/promote",
            json={"rule_text": "Regra customizada pelo operador."},
        )
    assert resp.status_code == 200
    assert resp.json()["rule"]["rule_text"] == "Regra customizada pelo operador."


@pytest.mark.asyncio
async def test_validate_nonexistent(client, db):
    with patch("app.routes.review.update_metadata"):
        resp = await client.post("/review/999/validate")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_promote_without_annotation(client, db):
    ep_id = await _create_edit_pair(db, annotation=None)

    with patch("app.routes.review.update_metadata"):
        resp = await client.post(f"/review/{ep_id}/promote")
    assert resp.status_code == 400
