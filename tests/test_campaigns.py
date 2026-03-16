"""Tests for bulk campaign functionality."""
import io
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from tests.conftest import make_webhook_payload


# --- CSV parsing and campaign creation ---

@pytest.mark.asyncio
async def test_create_campaign_from_csv(client, db):
    csv_content = "telefone,nome\n5511999990001,João\n5511999990002,Maria\n5511999990003,Pedro"
    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = await client.post(
        "/campaigns",
        data={"name": "Workshop Test", "base_message": "Oi {{nome}}, tudo bem?", "min_interval": "60", "max_interval": "180"},
        files={"csv_file": ("contacts.csv", csv_file, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["campaign"]["name"] == "Workshop Test"
    assert data["campaign"]["contact_count"] == 3
    assert data["campaign"]["status"] == "draft"


@pytest.mark.asyncio
async def test_create_campaign_deduplicates_phones(client, db):
    csv_content = "telefone,nome\n5511999990001,João\n5511999990001,João Dup\n5511999990002,Maria"
    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = await client.post(
        "/campaigns",
        data={"name": "Dedup Test", "base_message": "Oi", "min_interval": "60", "max_interval": "180"},
        files={"csv_file": ("contacts.csv", csv_file, "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["campaign"]["contact_count"] == 2


@pytest.mark.asyncio
async def test_create_campaign_rejects_invalid_csv(client, db):
    csv_content = "email,nome\nfoo@bar.com,João"
    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = await client.post(
        "/campaigns",
        data={"name": "Bad CSV", "base_message": "Oi", "min_interval": "60", "max_interval": "180"},
        files={"csv_file": ("contacts.csv", csv_file, "text/csv")},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_campaigns(client, db):
    csv_content = "telefone,nome\n5511999990001,João"
    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    await client.post(
        "/campaigns",
        data={"name": "Camp 1", "base_message": "Oi", "min_interval": "60", "max_interval": "180"},
        files={"csv_file": ("contacts.csv", csv_file, "text/csv")},
    )

    response = await client.get("/campaigns")
    assert response.status_code == 200
    campaigns = response.json()
    assert len(campaigns) == 1
    assert campaigns[0]["name"] == "Camp 1"
    assert campaigns[0]["pending"] == 1


@pytest.mark.asyncio
async def test_get_campaign_detail(client, db):
    csv_content = "telefone,nome\n5511999990001,João\n5511999990002,Maria"
    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    res = await client.post(
        "/campaigns",
        data={"name": "Detail Test", "base_message": "Oi {{nome}}", "min_interval": "60", "max_interval": "180"},
        files={"csv_file": ("contacts.csv", csv_file, "text/csv")},
    )
    campaign_id = res.json()["campaign"]["id"]

    response = await client.get(f"/campaigns/{campaign_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Detail Test"
    assert len(data["contacts"]) == 2
    assert data["pending"] == 2
    assert data["sent"] == 0


# --- Variation generation ---

@pytest.mark.asyncio
async def test_generate_variations(client, db):
    csv_content = "telefone,nome\n5511999990001,João"
    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    res = await client.post(
        "/campaigns",
        data={"name": "Var Test", "base_message": "Oi {{nome}}", "min_interval": "60", "max_interval": "180"},
        files={"csv_file": ("contacts.csv", csv_file, "text/csv")},
    )
    campaign_id = res.json()["campaign"]["id"]

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Var 1---VARIACAO---Var 2---VARIACAO---Var 3---VARIACAO---Var 4---VARIACAO---Var 5---VARIACAO---Var 6---VARIACAO---Var 7---VARIACAO---Var 8")]

    with patch("app.services.campaign_variations.get_anthropic_client") as mock_cls:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        response = await client.post(f"/campaigns/{campaign_id}/generate-variations")
        assert response.status_code == 200
        assert response.json()["count"] == 9  # 8 generated + 1 base message

    detail = await client.get(f"/campaigns/{campaign_id}")
    assert len(detail.json()["variations"]) == 9
    # First variation is the original base message (index -1)
    assert detail.json()["variations"][0]["variation_index"] == -1
    assert detail.json()["variations"][0]["variation_text"] == "Oi {{nome}}"


@pytest.mark.asyncio
async def test_edit_variation(client, db):
    csv_content = "telefone,nome\n5511999990001,João"
    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    res = await client.post(
        "/campaigns",
        data={"name": "Edit Var", "base_message": "Oi", "min_interval": "60", "max_interval": "180"},
        files={"csv_file": ("contacts.csv", csv_file, "text/csv")},
    )
    campaign_id = res.json()["campaign"]["id"]

    # Insert a variation directly
    await db.execute(
        "INSERT INTO campaign_variations (campaign_id, variation_index, variation_text) VALUES (?, 0, 'Original')",
        (campaign_id,),
    )
    await db.commit()

    response = await client.put(
        f"/campaigns/{campaign_id}/variations/0",
        json={"variation_text": "Edited text"},
    )
    assert response.status_code == 200

    row = await db.execute(
        "SELECT variation_text FROM campaign_variations WHERE campaign_id = ? AND variation_index = 0",
        (campaign_id,),
    )
    var = await row.fetchone()
    assert var["variation_text"] == "Edited text"


# --- Campaign executor ---

@pytest.mark.asyncio
async def test_executor_sends_and_marks_sent(db):
    from app.services.campaign_executor import _process_campaigns

    # Create campaign
    cursor = await db.execute(
        "INSERT INTO campaigns (name, base_message, status, min_interval, max_interval, next_send_at) VALUES ('Test', 'Oi {{nome}}', 'running', 60, 180, datetime('now'))"
    )
    campaign_id = cursor.lastrowid

    await db.execute(
        "INSERT INTO campaign_contacts (campaign_id, phone_number, name) VALUES (?, '5511999990001', 'João')",
        (campaign_id,),
    )
    await db.execute(
        "INSERT INTO campaign_variations (campaign_id, variation_index, variation_text) VALUES (?, 0, 'Oi {{nome}}, tudo bem?')",
        (campaign_id,),
    )
    await db.commit()

    with patch("app.services.campaign_executor.send_text_message", new_callable=AsyncMock) as mock_send, \
         patch("app.services.campaign_executor.manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()
        await _process_campaigns()

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][0] == "5511999990001"
        assert "João" in call_args[0][1]  # placeholder resolved

    # Check contact is marked sent
    row = await db.execute(
        "SELECT status FROM campaign_contacts WHERE campaign_id = ?", (campaign_id,)
    )
    contact = await row.fetchone()
    assert contact["status"] == "sent"


@pytest.mark.asyncio
async def test_executor_auto_pauses_after_5_failures(db):
    from app.services.campaign_executor import _process_campaigns

    cursor = await db.execute(
        "INSERT INTO campaigns (name, base_message, status, min_interval, max_interval, next_send_at, consecutive_failures) VALUES ('Test', 'Oi', 'running', 60, 180, datetime('now'), 4)"
    )
    campaign_id = cursor.lastrowid

    await db.execute(
        "INSERT INTO campaign_contacts (campaign_id, phone_number, name) VALUES (?, '5511999990001', 'João')",
        (campaign_id,),
    )
    await db.execute(
        "INSERT INTO campaign_variations (campaign_id, variation_index, variation_text) VALUES (?, 0, 'Oi')",
        (campaign_id,),
    )
    await db.commit()

    with patch("app.services.campaign_executor.send_text_message", new_callable=AsyncMock, side_effect=Exception("Connection lost")) as mock_send, \
         patch("app.services.campaign_executor.manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()
        await _process_campaigns()

    # Campaign should be blocked
    row = await db.execute("SELECT status FROM campaigns WHERE id = ?", (campaign_id,))
    campaign = await row.fetchone()
    assert campaign["status"] == "blocked"


@pytest.mark.asyncio
async def test_executor_completes_when_no_pending(db):
    from app.services.campaign_executor import _process_campaigns

    cursor = await db.execute(
        "INSERT INTO campaigns (name, base_message, status, min_interval, max_interval, next_send_at) VALUES ('Test', 'Oi', 'running', 60, 180, datetime('now'))"
    )
    campaign_id = cursor.lastrowid
    # No pending contacts
    await db.execute(
        "INSERT INTO campaign_contacts (campaign_id, phone_number, name, status) VALUES (?, '5511999990001', 'João', 'sent')",
        (campaign_id,),
    )
    await db.commit()

    with patch("app.services.campaign_executor.manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()
        await _process_campaigns()

    row = await db.execute("SELECT status FROM campaigns WHERE id = ?", (campaign_id,))
    campaign = await row.fetchone()
    assert campaign["status"] == "completed"


# --- Retry ---

@pytest.mark.asyncio
async def test_retry_resets_failed_contacts(client, db):
    cursor = await db.execute(
        "INSERT INTO campaigns (name, base_message, status, min_interval, max_interval) VALUES ('Test', 'Oi', 'completed', 60, 180)"
    )
    campaign_id = cursor.lastrowid

    await db.execute(
        "INSERT INTO campaign_contacts (campaign_id, phone_number, name, status) VALUES (?, '5511999990001', 'João', 'failed')",
        (campaign_id,),
    )
    await db.execute(
        "INSERT INTO campaign_contacts (campaign_id, phone_number, name, status) VALUES (?, '5511999990002', 'Maria', 'sent')",
        (campaign_id,),
    )
    await db.commit()

    response = await client.post(f"/campaigns/{campaign_id}/retry")
    assert response.status_code == 200

    # Failed contact should be pending again
    row = await db.execute(
        "SELECT status FROM campaign_contacts WHERE phone_number = '5511999990001' AND campaign_id = ?",
        (campaign_id,),
    )
    contact = await row.fetchone()
    assert contact["status"] == "pending"

    # Sent contact should remain sent
    row = await db.execute(
        "SELECT status FROM campaign_contacts WHERE phone_number = '5511999990002' AND campaign_id = ?",
        (campaign_id,),
    )
    contact = await row.fetchone()
    assert contact["status"] == "sent"

    # Campaign should be running
    row = await db.execute("SELECT status FROM campaigns WHERE id = ?", (campaign_id,))
    campaign = await row.fetchone()
    assert campaign["status"] == "running"


# --- Webhook campaign tagging ---

@pytest.mark.asyncio
async def test_webhook_tags_conversation_with_campaign(client, db):
    # Create a campaign with a sent contact
    cursor = await db.execute(
        "INSERT INTO campaigns (name, base_message, status) VALUES ('Tag Test', 'Oi', 'completed')"
    )
    campaign_id = cursor.lastrowid
    await db.execute(
        "INSERT INTO campaign_contacts (campaign_id, phone_number, name, status, sent_at) VALUES (?, '5511999990001', 'João', 'sent', datetime('now'))",
        (campaign_id,),
    )
    await db.commit()

    # Simulate webhook from that phone number
    with patch("app.routes.webhook.asyncio.create_task"):
        payload = make_webhook_payload(phone="5511999990001", text="Tenho interesse!", message_id="campaign-reply-1")
        response = await client.post("/webhook", json=payload)
        assert response.status_code == 200

    # Check conversation has origin_campaign_id
    row = await db.execute(
        "SELECT origin_campaign_id FROM conversations WHERE phone_number = '5511999990001'"
    )
    conv = await row.fetchone()
    assert conv["origin_campaign_id"] == campaign_id
