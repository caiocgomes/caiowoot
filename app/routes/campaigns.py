import csv
import io
import logging
import os
from pathlib import Path

import aiosqlite
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from fastapi.responses import PlainTextResponse

from app.config import settings
from app.database import get_db_connection
from app.services.campaign_variations import generate_variations
from app.websocket_manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/campaigns/csv-template")
async def download_csv_template():
    """Download a CSV template for campaign contacts."""
    content = "telefone,nome\n5511999999999,João Silva\n5511888888888,Maria Santos\n"
    return PlainTextResponse(
        content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contatos-template.csv"},
    )


@router.post("/campaigns")
async def create_campaign(
    db: aiosqlite.Connection = Depends(get_db_connection),
    name: str = Form(...),
    base_message: str = Form(...),
    csv_file: UploadFile = File(...),
    image: UploadFile | None = File(None),
    min_interval: int = Form(60),
    max_interval: int = Form(180),
):
    """Create a campaign from CSV upload."""
    # Parse CSV
    content = await csv_file.read()
    text = content.decode("utf-8-sig")  # handle BOM
    reader = csv.DictReader(io.StringIO(text))

    # Validate columns
    if not reader.fieldnames or "telefone" not in [f.strip().lower() for f in reader.fieldnames]:
        raise HTTPException(status_code=422, detail="CSV deve conter coluna 'telefone'")

    # Normalize fieldnames
    fieldname_map = {f.strip().lower(): f for f in reader.fieldnames}
    telefone_col = fieldname_map["telefone"]
    nome_col = fieldname_map.get("nome")

    contacts = []
    seen_phones = set()
    for row in reader:
        phone = row[telefone_col].strip()
        if not phone or phone in seen_phones:
            continue
        seen_phones.add(phone)
        contact_name = row.get(nome_col, "").strip() if nome_col else ""
        contacts.append((phone, contact_name or None))

    if not contacts:
        raise HTTPException(status_code=422, detail="CSV sem contatos válidos")

    # Save image if provided
    image_path = None
    if image and image.filename:
        img_dir = Path("data/campaign_images")
        os.makedirs(img_dir, exist_ok=True)
        import uuid
        ext = Path(image.filename).suffix or ".jpg"
        img_filename = f"{uuid.uuid4().hex}{ext}"
        image_path = str(img_dir / img_filename)
        img_data = await image.read()
        with open(image_path, "wb") as f:
            f.write(img_data)

    cursor = await db.execute(
        """INSERT INTO campaigns (name, base_message, image_path, min_interval, max_interval)
           VALUES (?, ?, ?, ?, ?)""",
        (name, base_message, image_path, min_interval, max_interval),
    )
    campaign_id = cursor.lastrowid

    for phone, cname in contacts:
        await db.execute(
            "INSERT INTO campaign_contacts (campaign_id, phone_number, name) VALUES (?, ?, ?)",
            (campaign_id, phone, cname),
        )

    await db.commit()

    return {
        "status": "ok",
        "campaign": {
            "id": campaign_id,
            "name": name,
            "status": "draft",
            "contact_count": len(contacts),
        },
    }


@router.get("/campaigns")
async def list_campaigns(db: aiosqlite.Connection = Depends(get_db_connection)):
    """List all campaigns with status counts."""
    rows = await db.execute(
        """SELECT c.id, c.name, c.status, c.created_at,
                  COUNT(cc.id) as total,
                  SUM(CASE WHEN cc.status = 'sent' THEN 1 ELSE 0 END) as sent,
                  SUM(CASE WHEN cc.status = 'failed' THEN 1 ELSE 0 END) as failed,
                  SUM(CASE WHEN cc.status = 'pending' THEN 1 ELSE 0 END) as pending
           FROM campaigns c
           LEFT JOIN campaign_contacts cc ON cc.campaign_id = c.id
           GROUP BY c.id
           ORDER BY c.created_at DESC"""
    )
    campaigns = await rows.fetchall()
    return [dict(c) for c in campaigns]


@router.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: int, db: aiosqlite.Connection = Depends(get_db_connection)):
    """Get campaign detail with contacts and variations."""
    row = await db.execute(
        """SELECT id, name, status, base_message, image_path,
                  min_interval, max_interval, created_at
           FROM campaigns WHERE id = ?""",
        (campaign_id,),
    )
    campaign = await row.fetchone()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    contacts_rows = await db.execute(
        """SELECT id, phone_number, name, status, error_message, sent_at
           FROM campaign_contacts
           WHERE campaign_id = ?
           ORDER BY id""",
        (campaign_id,),
    )
    contacts = await contacts_rows.fetchall()

    variations_rows = await db.execute(
        """SELECT id, variation_index, variation_text, usage_count, is_active
           FROM campaign_variations
           WHERE campaign_id = ?
           ORDER BY variation_index""",
        (campaign_id,),
    )
    variations = await variations_rows.fetchall()

    # Counts
    total = len(contacts)
    sent = sum(1 for c in contacts if c["status"] == "sent")
    failed = sum(1 for c in contacts if c["status"] == "failed")
    pending = sum(1 for c in contacts if c["status"] == "pending")

    return {
        **dict(campaign),
        "contacts": [dict(c) for c in contacts],
        "variations": [dict(v) for v in variations],
        "total": total,
        "sent": sent,
        "failed": failed,
        "pending": pending,
    }


@router.post("/campaigns/{campaign_id}/generate-variations")
async def generate_campaign_variations(campaign_id: int, db: aiosqlite.Connection = Depends(get_db_connection)):
    """Generate 8 message variations using Claude."""
    row = await db.execute(
        "SELECT id, base_message, status FROM campaigns WHERE id = ?",
        (campaign_id,),
    )
    campaign = await row.fetchone()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign["status"] != "draft":
        raise HTTPException(status_code=409, detail="Campaign must be in draft status")

    # Delete existing variations (except base message at index -1)
    await db.execute(
        "DELETE FROM campaign_variations WHERE campaign_id = ?",
        (campaign_id,),
    )

    # Insert base message as variation index -1 (original)
    await db.execute(
        "INSERT INTO campaign_variations (campaign_id, variation_index, variation_text) VALUES (?, ?, ?)",
        (campaign_id, -1, campaign["base_message"]),
    )

    # Generate 8 variations via Claude
    variations = await generate_variations(campaign["base_message"])

    for i, text in enumerate(variations):
        await db.execute(
            "INSERT INTO campaign_variations (campaign_id, variation_index, variation_text) VALUES (?, ?, ?)",
            (campaign_id, i, text),
        )

    await db.commit()

    return {"status": "ok", "count": len(variations) + 1}


class VariationUpdate(BaseModel):
    variation_text: str


@router.put("/campaigns/{campaign_id}/variations/{variation_idx}")
async def update_variation(campaign_id: int, variation_idx: int, req: VariationUpdate, db: aiosqlite.Connection = Depends(get_db_connection)):
    """Edit a single variation."""
    result = await db.execute(
        """UPDATE campaign_variations
           SET variation_text = ?
           WHERE campaign_id = ? AND variation_index = ?""",
        (req.variation_text, campaign_id, variation_idx),
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Variation not found")
    await db.commit()
    return {"status": "ok"}


@router.post("/campaigns/{campaign_id}/regenerate-variations")
async def regenerate_variations(campaign_id: int, db: aiosqlite.Connection = Depends(get_db_connection)):
    """Regenerate all variations."""
    return await generate_campaign_variations(campaign_id, db)


@router.patch("/campaigns/{campaign_id}/variations/{variation_id}/toggle")
async def toggle_variation(campaign_id: int, variation_id: int, db: aiosqlite.Connection = Depends(get_db_connection)):
    """Toggle a variation's active state."""
    row = await db.execute(
        "SELECT id, is_active FROM campaign_variations WHERE id = ? AND campaign_id = ?",
        (variation_id, campaign_id),
    )
    variation = await row.fetchone()
    if not variation:
        raise HTTPException(status_code=404, detail="Variation not found")

    # Check we're not deactivating the last active one
    if variation["is_active"]:
        count_row = await db.execute(
            "SELECT COUNT(*) as cnt FROM campaign_variations WHERE campaign_id = ? AND is_active = 1",
            (campaign_id,),
        )
        active_count = (await count_row.fetchone())["cnt"]
        if active_count <= 1:
            raise HTTPException(status_code=409, detail="Pelo menos uma variação deve ficar ativa")

    new_state = 0 if variation["is_active"] else 1
    await db.execute(
        "UPDATE campaign_variations SET is_active = ? WHERE id = ?",
        (new_state, variation_id),
    )
    await db.commit()

    return {"status": "ok", "is_active": bool(new_state)}


@router.post("/campaigns/{campaign_id}/start")
async def start_campaign(campaign_id: int, db: aiosqlite.Connection = Depends(get_db_connection)):
    """Start a draft campaign."""
    row = await db.execute(
        "SELECT id, status FROM campaigns WHERE id = ?", (campaign_id,)
    )
    campaign = await row.fetchone()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign["status"] != "draft":
        raise HTTPException(status_code=409, detail="Campaign must be in draft status to start")

    # Check active variations exist
    var_row = await db.execute(
        "SELECT COUNT(*) as cnt FROM campaign_variations WHERE campaign_id = ? AND is_active = 1",
        (campaign_id,),
    )
    var_count = (await var_row.fetchone())["cnt"]
    if var_count == 0:
        raise HTTPException(status_code=409, detail="Pelo menos uma variação deve estar ativa")

    await db.execute(
        "UPDATE campaigns SET status = 'running', next_send_at = datetime('now') WHERE id = ?",
        (campaign_id,),
    )
    await db.commit()

    await manager.broadcast(0, {
        "type": "campaign_status",
        "campaign_id": campaign_id,
        "status": "running",
    })

    return {"status": "ok"}


@router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: int, db: aiosqlite.Connection = Depends(get_db_connection)):
    """Pause a running campaign."""
    row = await db.execute(
        "SELECT id, status FROM campaigns WHERE id = ?", (campaign_id,)
    )
    campaign = await row.fetchone()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign["status"] != "running":
        raise HTTPException(status_code=409, detail="Campaign is not running")

    await db.execute(
        "UPDATE campaigns SET status = 'paused', next_send_at = NULL WHERE id = ?",
        (campaign_id,),
    )
    await db.commit()

    await manager.broadcast(0, {
        "type": "campaign_status",
        "campaign_id": campaign_id,
        "status": "paused",
    })

    return {"status": "ok"}


@router.post("/campaigns/{campaign_id}/resume")
async def resume_campaign(campaign_id: int, db: aiosqlite.Connection = Depends(get_db_connection)):
    """Resume a paused or blocked campaign."""
    row = await db.execute(
        "SELECT id, status FROM campaigns WHERE id = ?", (campaign_id,)
    )
    campaign = await row.fetchone()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign["status"] not in ("paused", "blocked"):
        raise HTTPException(status_code=409, detail="Campaign must be paused or blocked to resume")

    await db.execute(
        """UPDATE campaigns
           SET status = 'running', next_send_at = datetime('now'), consecutive_failures = 0
           WHERE id = ?""",
        (campaign_id,),
    )
    await db.commit()

    await manager.broadcast(0, {
        "type": "campaign_status",
        "campaign_id": campaign_id,
        "status": "running",
    })

    return {"status": "ok"}


@router.post("/campaigns/{campaign_id}/retry")
async def retry_failed(campaign_id: int, db: aiosqlite.Connection = Depends(get_db_connection)):
    """Retry all failed contacts with new variations."""
    row = await db.execute(
        "SELECT id, status FROM campaigns WHERE id = ?", (campaign_id,)
    )
    campaign = await row.fetchone()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Reset failed contacts to pending
    await db.execute(
        """UPDATE campaign_contacts
           SET status = 'pending', error_message = NULL
           WHERE campaign_id = ? AND status = 'failed'""",
        (campaign_id,),
    )

    # Set campaign to running
    await db.execute(
        """UPDATE campaigns
           SET status = 'running', next_send_at = datetime('now'), consecutive_failures = 0
           WHERE id = ?""",
        (campaign_id,),
    )
    await db.commit()

    await manager.broadcast(0, {
        "type": "campaign_status",
        "campaign_id": campaign_id,
        "status": "running",
    })

    return {"status": "ok"}
