import pytest


@pytest.mark.asyncio
async def test_create_rule(client, db):
    resp = await client.post("/rules", json={"rule_text": "Sempre qualificar antes de precificar."})
    assert resp.status_code == 200
    data = resp.json()
    assert data["rule_text"] == "Sempre qualificar antes de precificar."
    assert data["is_active"] == 1


@pytest.mark.asyncio
async def test_list_rules(client, db):
    await client.post("/rules", json={"rule_text": "Regra 1"})
    await client.post("/rules", json={"rule_text": "Regra 2"})

    resp = await client.get("/rules")
    assert resp.status_code == 200
    rules = resp.json()["rules"]
    assert len(rules) == 2


@pytest.mark.asyncio
async def test_update_rule(client, db):
    create_resp = await client.post("/rules", json={"rule_text": "Regra original"})
    rule_id = create_resp.json()["id"]

    resp = await client.put(f"/rules/{rule_id}", json={"rule_text": "Regra atualizada"})
    assert resp.status_code == 200
    assert resp.json()["rule_text"] == "Regra atualizada"


@pytest.mark.asyncio
async def test_toggle_rule(client, db):
    create_resp = await client.post("/rules", json={"rule_text": "Toggle test"})
    rule_id = create_resp.json()["id"]
    assert create_resp.json()["is_active"] == 1

    resp = await client.patch(f"/rules/{rule_id}/toggle")
    assert resp.status_code == 200
    assert resp.json()["is_active"] == 0

    resp = await client.patch(f"/rules/{rule_id}/toggle")
    assert resp.json()["is_active"] == 1


@pytest.mark.asyncio
async def test_update_nonexistent_rule(client, db):
    resp = await client.put("/rules/999", json={"rule_text": "Nope"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_rule_with_source(client, db):
    # Create a real edit pair to reference
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    await db.execute(
        "INSERT INTO edit_pairs (conversation_id, customer_message, original_draft, final_message, was_edited) VALUES (1, 'msg', 'draft', 'final', 1)"
    )
    await db.commit()

    resp = await client.post("/rules", json={"rule_text": "From annotation", "source_edit_pair_id": 1})
    assert resp.status_code == 200
    assert resp.json()["source_edit_pair_id"] == 1
